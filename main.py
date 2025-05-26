import datetime     # for time stamps
import csv          # for csv operations
import os           # for finding path
import pandas as pd # for data manipulation
import cv2          # OpenCV for image operations
from pyzbar.pyzbar import decode # QR code decode
import easyocr      # For Optical Character Recognition
import re           # For regular expressions used in OCR text extraction

# --- Configuration Constants ---
LOG_FILE = 'traceability_log.csv'       
PRODUCT_DATA_FILE = 'products.csv'      
LABEL_IMAGE_FOLDER = 'label_images/'    
BLUR_THRESHOLD = 99.99                   

print("Smart Labeling System Initializing... ")

# Initializing EasyOCR (once)
print("Initializing EasyOCR reader... (May take some time)")
try:
    easyocr_reader = easyocr.Reader(['en'], gpu=True) # English, GPU
    print("EasyOCR reader initialized successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize EasyOCR Reader: {e}")
    easyocr_reader = None 

# Functions

# Function to clean the extracted OCR text
def clean_ocr_text(text_to_clean):
    if not isinstance(text_to_clean, str):
        return "" 
    
    cleaned = text_to_clean.upper()
    # Correction to letters and numbers
    cleaned = cleaned.replace("O", "0")
    cleaned = cleaned.replace("I", "1")
    cleaned = cleaned.replace("L", "1")
    cleaned = cleaned.replace("Z", "2")
    cleaned = cleaned.replace("B", "8") 
    cleaned = cleaned.replace("S", "5") 

    cleaned = cleaned.replace("BATCH:", "").replace("S/N:", "").replace("SIN:", "")
    cleaned = cleaned.replace(" ", "")
    return cleaned.strip()

# Extract the BatchID and SerialNumber from the label.
def extract_specific_ocr_info(ocr_text_list):
    extracted_info = {'batch': None, 'serial': None}
    
    for text_element in ocr_text_list:
        text_upper = str(text_element).upper()

        batch_match = re.search(r'(?:BATCH\s*[:\s]*)?(B)([0-9A-Z]{3,})', text_upper)
        if batch_match and not extracted_info['batch']: 
            prefix = batch_match.group(1) 
            alphanum_part = batch_match.group(2)
            cleaned_alphanum = alphanum_part.replace("O","0").replace("I","1").replace("L","1").replace("S","5").replace("B","8").replace("Z","2")
            extracted_info['batch'] = prefix + cleaned_alphanum

        serial_match = re.search(r'(?:S[/\\]N\s*[:\s]*|SIN\s*[:\s]*)?(SN)([0-9A-Z]{3,})', text_upper)
        if serial_match and not extracted_info['serial']: 
            prefix = serial_match.group(1) 
            alphanum_part = serial_match.group(2)
            cleaned_alphanum = alphanum_part.replace("O","0").replace("I","1").replace("L","1").replace("S","5").replace("B","8").replace("Z","2")
            extracted_info['serial'] = prefix + cleaned_alphanum
            
    return extracted_info

#Load product data from products.csv
def load_product_data(file_path):
    """load from the CSV file using pandas""" 
    try:
        df = pd.read_csv(file_path) #read the csv in the format of pandas dataframe
        # Convert RoHS_Compliant column to boolean
        if 'RoHS_Compliant' in df.columns:
            df['RoHS_Compliant'] = df['RoHS_Compliant'].astype(str).str.upper().map(
                {'TRUE': True, 'FALSE': False, 'COMPLIANT': True, 'NON-COMPLIANT': False}
            ).fillna(False) # Handle other values or  defaulting to False

        print(f"Successfully loaded {len(df)} products from '{file_path}'.")
        return df.to_dict('records') #convert the dataframe in to a dict
    except FileNotFoundError:
        print(f"ERROR: product data file '{file_path}' not found, please create it.")
        return []
    except Exception as e:
        print(f"ERROR: Could not read product data file '{file_path}': {e}")
        return [] #return an empty list on all other errors

def get_label_image_path(product_data, base_folder):
    """Determines the file path for a product's label image."""
    expected_serial_qr = product_data.get('Expected_SerialNumber_QR', '') # Default to empty string

    #specific cases for test image filenames
    if expected_serial_qr == 'SN004_MISMATCH':
        image_filename = 'SN004.png'
    elif expected_serial_qr == 'SN_FAIL_BLURRY_EXPECTED':
        image_filename = 'SN_FAIL_BLURRY.png'
    else:
        image_filename = f"{expected_serial_qr}.png"

    return os.path.join(base_folder, image_filename)

# Check the label quality before proceeding
def check_image_quality(cv2_image_object):
    """image quality check by openCV""" 
    if cv2_image_object is None:
        return False, "Image object is None"
    
    gray = cv2.cvtColor(cv2_image_object, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    if variance < BLUR_THRESHOLD:
        return False, f"FAIL_QUALITY_BLURRY (Variance: {variance:.2f})"
    return True, f"PASS_QUALITY (Variance: {variance:.2f})"

# Function to read QR code
def read_qr_from_image(cv2_image_object):
    if cv2_image_object is None: 
        return False, None, "QR_FAIL_NO_IMAGE"
    
    try:
        decoded_objects = decode(cv2_image_object) #pyzbar decode function
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode('utf-8')
            return True, qr_data, f"QR_READ_SUCCESS ({qr_data})"
        else:
            return False, None, "QR_FAIL_NOT_FOUND"
    except Exception as e:
        return False, None, f"QR_FAIL_EXCEPTION ({e})"

# Function to read text with OCR
def read_text_from_label_ocr(cv2_image_object, reader): 
    if reader is None:
        return False, [], "OCR_FAIL_NO_READER"
    if cv2_image_object is None: 
        return False, [], "OCR_FAIL_NO_IMAGE"
    
    try:
        ocr_result = reader.readtext(cv2_image_object)
        if ocr_result:
            detected_texts = [result[1] for result in ocr_result] # Extract text strings
            return True, detected_texts, "OCR_READ_SUCCESS"
        else:
            return False, [], "OCR_INFO_NO_TEXT_DETECTED"
    except Exception as e:
        return False, [], f"OCR_FAIL_EXCEPTION ({e})"
    
# Compliance Check(RoHS Compliance)
def verify_product_compliance(product_data):
    device_id = product_data['DeviceID']
    print(f"  STEP 2: VERIFYING COMPLIANCE for {device_id}:")

    #1. Check RoHS Compliance
    is_rohs_ok = product_data.get('RoHS_Compliant', False) 

    if not is_rohs_ok:
        compliance_msg = f"FAIL_RoHS: {device_id} not compliant"
        print(f"    {compliance_msg}") 
        return False, compliance_msg 
    else:
        compliance_msg = f"PASS_RoHS: {device_id} compliant"
        print(f"    {compliance_msg}")
        return True, compliance_msg 

# Create the log file and initialize the headers if it doesnt exist
def initialize_log_file():

    fieldnames = [
        'Timestamp', 
        'DeviceID', 
        'BatchID', 
        'OverallStatus',
        'ComplianceStatus', 
        'ImageQualityStatus',
        'QR_ReadData', 
        'QR_MatchStatus',
        'OCR_ExtractedBatch', 
        'OCR_BatchMatch',
        'OCR_ExtractedSerial', 
        'OCR_SerialMatch',
        'ActionDetails'
    ]
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        print(f"Log file '{LOG_FILE}' created and header written.") 
    else:
        print(f"Log file '{LOG_FILE}' already existed. Header not rewritten.") 

# Logs an event (for one products processing result) to the CSV file using provided keyword arguments
def log_system_event(**kwargs):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Define all possible fields for consistency, defaulting to "N/A"
    log_entry = {
        'Timestamp': timestamp,
        'DeviceID': kwargs.get('device_id', "N/A"),
        'BatchID': kwargs.get('batch_id', "N/A"),
        'OverallStatus': kwargs.get('overall_status', "PENDING"),
        'ComplianceStatus': kwargs.get('compliance_status', "N/A"),
        'ImageQualityStatus': kwargs.get('image_quality_status', "N/A"),
        'QR_ReadData': kwargs.get('qr_read_data', "N/A"),
        'QR_MatchStatus': kwargs.get('qr_match_status', "N/A"),
        'OCR_ExtractedBatch': kwargs.get('ocr_extracted_batch', "N/A"),
        'OCR_BatchMatch': kwargs.get('ocr_batch_match', "N/A"),
        'OCR_ExtractedSerial': kwargs.get('ocr_extracted_serial', "N/A"),
        'OCR_SerialMatch': kwargs.get('ocr_serial_match', "N/A"),
        'ActionDetails': kwargs.get('action_details', "")
    }
    
    fieldnames = list(log_entry.keys())
    
    with open(LOG_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(log_entry)

    print(f"  Logged: {log_entry['DeviceID']} - {log_entry['OverallStatus']} (Details: {log_entry['ActionDetails']})")



# Main function
if __name__ == "__main__":
    initialize_log_file() # call this once
    product_list = load_product_data(PRODUCT_DATA_FILE)

    if not product_list:
        print("Exiting as no product data could be loaded.") 
    else:
        print(f"\nStarting process for {len(product_list)} products from CSV...") 

        #loop for processing each product
        for product_info in product_list:
            device_id = product_info.get('DeviceID', 'UNKNOWN_DEVICE')
            batch_id_from_csv = product_info.get('BatchID', 'UNKNOWN_BATCH').upper().strip()
            expected_qr_serial_from_csv = product_info.get('Expected_SerialNumber_QR', '').upper().strip()

            print(f"\n--- Processing product: {device_id} (Batch: {batch_id_from_csv}) ---")

            # Initialize variables
            current_status = "PENDING"
            action_summary = ""
            log_payload = {
                'device_id': device_id, 'batch_id': batch_id_from_csv,
                'compliance_status': "SKIPPED", 'image_quality_status': "SKIPPED",
                'qr_read_data': "N/A", 'qr_match_status': "SKIPPED",
                'ocr_extracted_batch': "N/A", 'ocr_batch_match': "SKIPPED",
                'ocr_extracted_serial': "N/A", 'ocr_serial_match': "SKIPPED"
            }

            #Step 1: Identify product(simulated)
            print(f"  STEP 1: Identifying product {device_id}...") 

            #STEP 2: Verifying compliance
            is_compliant, compliance_msg = verify_product_compliance(product_info)
            log_payload['compliance_status'] = compliance_msg

            if not is_compliant:
                current_status = "REJECTED"
                action_summary = f"Compliance Failure ({compliance_msg})"
                print(f"    ACTION_SIM: Simulating rejection of {device_id} due to: {compliance_msg}")
                print(f"--- product {device_id} process is halted due to compliance failure ---")
                log_system_event(overall_status=current_status, action_details=action_summary, **log_payload)
                continue 

            #STEP 3: Load label image
            print(f"  STEP 3: Loading label image for {device_id}...") 
            label_image_path = get_label_image_path(product_info, LABEL_IMAGE_FOLDER)
            cv_image = None
            
            if not os.path.exists(label_image_path):
                image_load_err_msg = f"FAIL_IMAGE_NOT_FOUND ({label_image_path})"
                print(f"    ERROR: {image_load_err_msg}") 
                log_payload['image_quality_status'] = image_load_err_msg
                current_status = "REJECTED"
                action_summary = "Image not found for label."
            else:
                cv_image = cv2.imread(label_image_path)
                if cv_image is None:
                    image_load_err_msg = f"FAIL_IMAGE_LOAD_ERROR ({label_image_path})"
                    print(f"    ERROR: Could not load image from '{label_image_path}' using OpenCV.") 
                    log_payload['image_quality_status'] = image_load_err_msg
                    current_status = "REJECTED"
                    action_summary = "Error loading label image."
                else:
                    print(f"    SUCCESS: Label image '{label_image_path}' loaded.") 
                    # STEP 3b: Check Image Quality
                    quality_ok, quality_msg = check_image_quality(cv_image)
                    log_payload['image_quality_status'] = quality_msg
                    if not quality_ok:
                        current_status = "REJECTED"
                        action_summary = f"Image Quality Failure ({quality_msg})"
                        print(f"    IMAGE_QUALITY_CHECK: {quality_msg}") 
                    else:
                        print(f"    IMAGE_QUALITY_CHECK: {quality_msg}")
                        # Image quality is OK, proceed to AI checks

            if current_status == "REJECTED": # If image load or quality check failed
                print(f"    ACTION_SIM: Simulating rejection of {device_id} due to: {action_summary}")
                print(f"--- product {device_id} process is halted. ---") 
                log_system_event(overall_status=current_status, action_details=action_summary, **log_payload)
                continue

            #STEP 4a: AI - Read QR Code
            print(f"STEP 4a: Attempting QR Code Read for {device_id}...") # Your print
            qr_read_success, qr_data, qr_msg = read_qr_from_image(cv_image)
            log_payload['qr_read_data'] = qr_data
            log_payload['qr_match_status'] = qr_msg # Store raw read message initially
            print(f"    QR Read attempt result: {qr_msg}") # Your print

            qr_content_match = False
            if qr_read_success:
                # Ensure qr_data is also cleaned (uppercased, stripped) for fair comparison
                if qr_data and qr_data.strip().upper() == expected_qr_serial_from_csv: # expected_qr_serial_from_csv is already cleaned
                    qr_content_match = True
                    log_payload['qr_match_status'] = "MATCH"
                else:
                    log_payload['qr_match_status'] = f"MISMATCH (Exp:{expected_qr_serial_from_csv}, Got:{qr_data.strip().upper() if qr_data else 'None'})"
            # else qr_read_success is False, qr_match_status retains the failure message from qr_msg

            if not (qr_read_success and qr_content_match):
                # If QR fails or mismatches, we might still proceed to OCR for data gathering,
                # but the overall status will likely be REJECTED.
                current_status = "REJECTED" # Tentative, can be overridden if OCR somehow passes and we change logic
                action_summary = f"QR Validation Failed ({log_payload['qr_match_status']})"
                # No 'continue' here yet, let OCR run for data gathering.

            #STEP 4b: AI label check (OCR)
            print(f"  STEP 4b: Attempting OCR text read for {device_id}...") # Your print (modified)
            ocr_batch_match_status, ocr_serial_match_status = "SKIPPED", "SKIPPED"
            ocr_extracted_batch, ocr_extracted_serial = None, None

            if easyocr_reader and cv_image is not None: 
                ocr_success, ocr_texts_list, ocr_read_msg = read_text_from_label_ocr(cv_image, easyocr_reader)
                print(f"    OCR Read attempt result: {ocr_read_msg}")

                if ocr_success:
                    extracted_ocr_data = extract_specific_ocr_info(ocr_texts_list)
                    ocr_extracted_batch = extracted_ocr_data.get('batch')
                    ocr_extracted_serial = extracted_ocr_data.get('serial')
                    log_payload['ocr_extracted_batch'] = ocr_extracted_batch
                    log_payload['ocr_extracted_serial'] = ocr_extracted_serial

                    # Validate OCR Batch against BatchID from CSV
                    if ocr_extracted_batch:
                        # expected_batch_from_csv is already cleaned (uppercased, stripped)
                        if ocr_extracted_batch == batch_id_from_csv:
                            ocr_batch_match_status = "MATCH"
                        else:
                            ocr_batch_match_status = f"MISMATCH (Exp:{batch_id_from_csv}, Got:{ocr_extracted_batch})"
                    else:
                        ocr_batch_match_status = "NOT_FOUND_IN_OCR"
                    log_payload['ocr_batch_match'] = ocr_batch_match_status
                    
                    # Validate OCR Serial against Expected_SerialNumber_QR from CSV
                    if ocr_extracted_serial:
                        # expected_qr_serial_from_csv is already cleaned (uppercased, stripped)
                        if ocr_extracted_serial == expected_qr_serial_from_csv:
                            ocr_serial_match_status = "MATCH"
                        else:
                            ocr_serial_match_status = f"MISMATCH (Exp:{expected_qr_serial_from_csv}, Got:{ocr_extracted_serial})"
                    else:
                        ocr_serial_match_status = "NOT_FOUND_IN_OCR"
                    log_payload['ocr_serial_match'] = ocr_serial_match_status
                    print(f"    OCR Validation: Batch Check='{ocr_batch_match_status}', Serial Check='{ocr_serial_match_status}'")
                else: # OCR read failed or no text found
                    ocr_batch_match_status = ocr_read_msg # Log the OCR read status (e.g., "OCR_INFO_NO_TEXT_DETECTED")
                    ocr_serial_match_status = ocr_read_msg
                    log_payload['ocr_batch_match'] = ocr_batch_match_status
                    log_payload['ocr_serial_match'] = ocr_serial_match_status
            elif not easyocr_reader:
                ocr_read_msg = "OCR_FAIL_NO_READER"
                log_payload['ocr_batch_match'] = ocr_read_msg
                log_payload['ocr_serial_match'] = ocr_read_msg
                print(f"    OCR Read attempt result: {ocr_read_msg}")
            else: # cv_image was None
                ocr_read_msg = "OCR_FAIL_NO_IMAGE"
                log_payload['ocr_batch_match'] = ocr_read_msg
                log_payload['ocr_serial_match'] = ocr_read_msg
                print(f"    OCR Read attempt result: {ocr_read_msg}")

            #STEP 5: Final Overall decision
            # Re-evaluate current_status based on all checks
            # If it was already REJECTED (e.g. by QR fail), this won't change it to ACCEPTED
            # but if QR was OK, OCR could still make it REJECTED.
            if is_compliant and qr_content_match and ocr_batch_match_status == "MATCH" and ocr_serial_match_status == "MATCH":
                current_status = "ACCEPTED"
                action_summary = "All checks passed (Compliance, Image Quality, QR, OCR)."
            else: # Some check failed
                current_status = "REJECTED" # Ensure it's marked rejected if not already
                if not is_compliant: # Should have been caught earlier
                    action_summary = f"Compliance Failure ({compliance_msg})"
                elif not log_payload['image_quality_status'].startswith("PASS"): # Check the actual status string
                    action_summary = f"Image Quality Failure ({log_payload['image_quality_status']})"
                elif not (qr_read_success and qr_content_match):
                    action_summary = f"QR Validation Failed ({log_payload['qr_match_status']})"
                elif ocr_batch_match_status != "MATCH":
                    action_summary = f"OCR Batch Validation Failed ({ocr_batch_match_status})."
                elif ocr_serial_match_status != "MATCH":
                    action_summary = f"OCR Serial Validation Failed ({ocr_serial_match_status})."
                else: 
                    action_summary = "Validation Failed (Unknown Reason)."
            
            #STEP 6: Simulate Actuator action
            print(f"    ACTION_SIM: {action_summary}") # Your print (modified)

            log_system_event(overall_status=current_status, action_details=action_summary, **log_payload)

        print("\n--- All Products Processed ---") 
        print(f"Check '{LOG_FILE}' for details.")