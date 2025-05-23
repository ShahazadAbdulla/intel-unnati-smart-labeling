import datetime     # for time stamps
import csv          # for creating the log file
import os           # for finding path
import pandas as pd #
import cv2          #OpenCV
from pyzbar.pyzbar import decode #QR code decode 

LOG_FILE = 'traceability_log.csv'       # for the results storing
PRODUCT_DATA_FILE = 'products.csv'      # for taking the products list to verify
LABEL_IMAGE_FOLDER = 'label_images/'    # label image folder

print ("Smart Labeling System Initializing... ")

#hardcoded sample data
# sample_product_data = [
#     {'DeviceID': 'ELEC001', 'BatchID': 'B001', 'Expected_SerialNumber_QR': 'SN001'},
#     {'DeviceID': 'ELEC002', 'BatchID': 'B001', 'Expected_SerialNumber_QR': 'SN002'},
#     {'DeviceID': 'ELEC003', 'BatchID': 'B002', 'Expected_SerialNumber_QR': 'SN003'}
# ]

#function to load the products
def load_product_data(file_path):
    """load from the CSV file using pandas"""
    try:
        #read the csv in the format of pandas dataframe
        df = pd.read_csv(file_path)
        if 'RoHS_Compliant' in df.columns:
            df['RoHS_Compliant'] = df['RoHS_Compliant'].astype(str).str.upper().map({'TRUE': True, 'FALSE': False})

        print(f"Successfully loaded {len(df)} products from '{file_path}.")
        #convert the dataframe in to a dict
        return df.to_dict('records')
    except FileNotFoundError:
        print(f"ERROR: product data file '{file_path} not found, please create it.")
    except Exception as e:
        print(f"ERROR: Could not read product data file '{file_path}': {e}")
        return [] #return an empty list on all other errors
    
#get label images path
def get_label_image_path(product_data, base_folder):
    expected_serial = product_data.get('Expected_SerialNumber_QR')

    #specific cases
    if expected_serial == 'SN004_MISMATCH':
        image_filename = 'SN004.png'
    elif expected_serial == 'SN_FAIL_BLURRY_EXPECTED':
        image_filename = 'SN_FAIL_BLURRY.png'
    else:
        image_filename = f"{expected_serial}.png"

    image_path = os.path.join(base_folder, image_filename)
    return image_path

#function to read QR code
def read_qr_code_from_image(cv2_image_object):
    if cv2_image_object is None:
        return False, None, "ERROR: Image object is None, cannot read QR"
    
    try:
        decoded_objects = decode(cv2_image_object)
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode('utf-8') #pyzbar decode function
            return True, qr_data, f"SUCCESS: QR decoded data: {qr_data}"
        else:
            return False, None, "FAIL: No QR code found or could not be decoded"
    except Exception as e:
        return False, None, "ERROR: Excepion during QR code decoding: {e}"
    
#verifying compliance
def verify_compliance(product_data):
    """check compliance for MVP RoHS is checked to be T/F and logged"""
    device_id = product_data['DeviceID']
    print(f"VERIFYING COMPLIANCE for {device_id}:") #info print

    #1. Check RoHS Compliance
    #Check if available if not make it false
    is_rohs_ok = product_data.get('RoHS_Compliant', False)

    if not is_rohs_ok:
        compliance_msg = f"FAIL_RoHS: {device_id} is not RoHS Compliant"
        print(f"        {compliance_msg}")
        return False, compliance_msg #Product failed compliance
    else:
        compliance_msg = f"PASS_RoHS: {device_id} is RoHS Compliant"
        print(f"        {compliance_msg}")
        return True, compliance_msg #Product passed compliance

#function to initialize log file
def initialize_log_file():
    """creates the log file and initialize the headers if it doesnt exist"""
    fieldNames = ['Timestamp', 'DeviceID', 'BatchID', 'ComplianceDetails', 'QR_DataRead', 'QR_MatchStatus', 'OCR_Details', 'OverallStatus', 'ActionDetails']

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
            writer.writeheader()
        print(f"Log file '{LOG_FILE}' created and header written,")
    else:
        print(f"Log file '{LOG_FILE}' already existed. Header not rewritten")

#function to log an event
def log_event(device_id, batch_id, compliance_details, qr_data_read, qr_match_status, ocr_details, overall_status, action_details):
    """Logs an event (for one products processing result) to the CSV file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'Timestamp': timestamp,
        'DeviceID': device_id,
        'BatchID': batch_id,
        'ComplianceDetails': compliance_details,
        'QR_DataRead': qr_data_read,
        'QR_MatchStatus': qr_match_status,
        'OCR_Details': ocr_details,
        'OverallStatus': overall_status,
        'ActionDetails': action_details
    }
    with open(LOG_FILE, 'a', newline='') as csvfile:
        fieldNames = ['Timestamp', 'DeviceID', 'BatchID', 'ComplianceDetails', 'QR_DataRead', 'QR_MatchStatus', 'OCR_Details', 'OverallStatus', 'ActionDetails']
        writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
        writer.writerow(log_entry)
    print(f"Logged: {device_id} - {overall_status} (compliance: {compliance_details})")

#main function
if __name__ == "__main__":
    initialize_log_file() # call this once in the beginning
    product_list = load_product_data(PRODUCT_DATA_FILE)

    if not product_list:
        print("Exiting as no product data could be loaded")
    else:
        print(f"\nStarting process for {len(product_list)} products from CSV...")

        #loop
        for product_info in product_list:

            # extract basic info
            device_id = product_info['DeviceID']
            batch_id = product_info['BatchID']
            expected_serial_from_csv = product_info.get('Expected_SerialNumber_QR', 'N/A_EXPECTED_SERIAL')

            #other fields
            rohs_compliant = product_info['RoHS_Compliant']

            print(f"\n--- Processing product: {device_id} (Batch: {batch_id}) ---")

            #Step 1: Identify product(simulated)
            print(f" STEP 1: Identifying product {device_id}...")
            #in this version identification is just having the product info from the list

            #STEP 2: Verifying compliance
            is_compliant, compliance_log_msg = verify_compliance(product_info)

            #initialize AI check var
            qr_read_success = False
            actual_qr_data = None
            qr_validation_msg = "QR_CHECK_SKIPPED_DUE_TO_COMPLIANCE_FAIL"

            #if compliance failed log and skip to the next product
            if not is_compliant:
                overall_product_status = "REJECTED"
                action_details = f"product rejected at compliance stage" 

                #log the failure
                log_event(
                    device_id=device_id,
                    batch_id=batch_id,
                    compliance_details=compliance_log_msg,
                    qr_data_read=actual_qr_data,
                    qr_match_status=qr_validation_msg,
                    ocr_details=ocr_read_placeholder,
                    overall_status=overall_product_status,
                    action_details=action_details
                )

                print(f" ACTION_SIM: Simulating rejection of {device_id} due to: {compliance_log_msg}")
                print(f"--- product {device_id} process is halted due to compliance failure ---")
                continue

            #STEP 3: Load label image 
            print(f" STEP 3: Loading label image for {device_id}...")
            label_image_path = get_label_image_path(product_info, LABEL_IMAGE_FOLDER)

            if not os.path.exists(label_image_path):
                print(f"ERROR: label image not found at '{label_image_path}'")
                qr_validation_msg = "FAIL_IMAGE_NOT_FOUND"
            else:
                cv_image = cv2.imread(label_image_path)
                if cv_image is None:
                    print(f"    ERROR: Could not load image from '{label_image_path}' using OpenCV.")
                    qr_validation_msg = "FAIL_IMAGE_LOAD_ERROR"
                else:
                    print(f"   SUCCESS: Label image '{label_image_path}' loaded.")
                    # Step 4a: AI - Read QR Code
                    print(f"    STEP 4a: Attempting QR Code Read for {device_id}...")
                    qr_read_success, actual_qr_data, qr_decode_msg = read_qr_code_from_image(cv_image)
                    print(f"    QR Read attempt result: {qr_decode_msg}")
                    qr_validation_msg = qr_decode_msg # For logging the raw decode message                

            #STEP 4b: AI label check (OCR)
            print(f" STEP 4b: Simulating OCR text read for {device_id}...")
            ocr_read_placeholder = "PENDING_OCR_READ"

            #STEP 5: Overall decision(includes QR)
            qr_content_matches_expected = False
            if qr_read_success and actual_qr_data is not None:
                if actual_qr_data == expected_serial_from_csv:
                    qr_content_matches_expected = True
                    qr_validation_msg = " MATCH"
                else:
                    qr_validation_msg = f"MISMATCH (Exp:{expected_serial_from_csv},Got:{actual_qr_data})"
            elif cv_image is not None and not qr_read_success:
                qr_validation_msg = "NO_QR_DETECTED"

            #over product status
            if is_compliant and qr_read_success and qr_content_matches_expected:
                overall_product_status = "ACCEPTED"
                action_details = "All check passed (Compliance, QR read and match). Product accepted"
            elif is_compliant and (not qr_read_success or not qr_content_matches_expected):
                overall_product_status = "REJECTED"
                action_details = f"Product rejected after AI check. Compliance: OK, QR status: {qr_validation_msg}"

            #STEP 6: Simulate Actuator action
            print(f"    ACTION_SIM: {action_details}")

            #log the details for now as in placeholder for the product
            log_event(device_id=device_id, batch_id=batch_id, compliance_details=compliance_log_msg, qr_data_read=actual_qr_data, qr_match_status=qr_validation_msg, ocr_details=ocr_read_placeholder, overall_status=overall_product_status, action_details=action_details)

        print("\n--- All Sample Products Processed ---")
        print(f"Check '{LOG_FILE}' for details")