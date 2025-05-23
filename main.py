import datetime     # for time stamps
import csv          # for creating the log file
import os           # for finding path
import pandas as pd #

LOG_FILE = 'traceability_log.csv'   # for the results storing
PRODUCT_DATA_FILE = 'products.csv'  # for taking the products list to verify
# label.csv will be created later

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
    fieldNames = ['Timestamp', 'DeviceID', 'BatchID', 'ComplianceDetails', 'OverallStatus', 'ActionDetails']

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
            writer.writeheader()
        print(f"Log file '{LOG_FILE}' created and header written,")
    else:
        print(f"Log file '{LOG_FILE}' already existed. Header not rewritten")

#function to log an event
def log_event(device_id, batch_id, compliance_details, overall_status, action_details):
    """Logs an event (for one products processing result) to the CSV file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        'Timestamp': timestamp,
        'DeviceID': device_id,
        'BatchID': batch_id,
        'ComplianceDetails': compliance_details,
        'OverallStatus': overall_status,
        'ActionDetails': action_details
    }
    with open(LOG_FILE, 'a', newline='') as csvfile:
        fieldNames = ['Timestamp', 'DeviceID', 'BatchID', 'ComplianceDetails', 'OverallStatus', 'ActionDetails']
        writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
        writer.writerow(log_entry)
    print(f"Logged: {device_id} - {overall_status} (compliance: {compliance_details})")

#main function
if __name__ == "__main__":
    initialize_log_file() # call this once in the beginning
    product_list = load_product_data(PRODUCT_DATA_FILE)

    if not property:
        print("Exiting as no product data could be loaded")
    else:
        print(f"\nStarting process for {len(product_list)} products from CSV...")

        #loop
        for product_info in product_list:

            # extract basic info
            device_id = product_info['DeviceID']
            batch_id = product_info['BatchID']

            #other fields
            rohs_compliant = product_info['RoHS_Compliant']
            expected_qr = product_info['Expected_SerialNumber_QR']

            print(f"\n--- Processing product: {device_id} (Batch: {batch_id}) ---")

            #Step 1: Identify product(simulated)
            print(f" STEP 1: Identifying product {device_id}...")
            #in this version identification is just having the product info from the list

            #STEP 2: Verifying compliance
            is_compliant, compliance_log_msg = verify_compliance(product_info)

            #if compliance failed log and skip to the next product
            if not is_compliant:
                overall_product_status = "REJECTED"
                action_details = f"product rejected at compliance stage" 

                #log the failure
                log_event(
                    device_id=device_id,
                    batch_id=batch_id,
                    compliance_details=compliance_log_msg,
                    overall_status=overall_product_status,
                    action_details=action_details
                )

                print(f" ACTION_SIM: Simulating rejection of {device_id} due to: {compliance_log_msg}")
                print(f"--- product {device_id} process is halted due to compliance failure ---")
                continue

            #STEP 3: Load label image
            print(f" STEP 3: Simulating loading label image for {device_id}...")

            #STEP 4: AI label check (QR and OCR)
            print(f" STEP 4a: Simulating QR code read for {device_id}...")
            qr_read_placeholder = "PENDING_QR_READ" 
            print(f" STEP 4b: Simulating OCR text read for {device_id}...")
            ocr_read_placeholder = "PENDING_OCR_READ"

            #STEP 5: Overall decision
            overall_product_status_if_compliant = "PENDING_AI_CHECKS"

            #STEP 6: Simulate Actuator action
            action_details_if_compliant =  "Compliance is okay. Awaiting AI label validation"

            print(f"Simulating actuator action: {action_details_if_compliant}")

            #log the details for now as in placeholder for the product
            log_event(device_id=device_id, batch_id=batch_id, compliance_details=compliance_log_msg, overall_status=overall_product_status_if_compliant, action_details=action_details_if_compliant)

        print("\n--- All Sample Products Processed ---")
        print(f"Check '{LOG_FILE}' for details")