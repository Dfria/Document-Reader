import pdfplumber
import spacy
from datetime import datetime
import os
import re
import pandas as pd
import csv

nlp = spacy.load("en_core_web_sm")

# =============================== extract_dir(dir_path): Returns Panda's DataFrame of these columns =============================== 
    # policy-number: policy_number
    # primary-insured: primary_insured
    # secondary-insured: secondary_insured
    # mailing-address: mailing_address
    # transaction-type: transaction_type
    # insurer: insurer
    # effective-date: effective_date
    # expiration-date: expiration_date
    # premium: premium
    # policy-fee: policy_fee
    # sl-tax: sl_tax
    # stamping-fee: stamping_fee
    # total-premium: total_premium

def extract_dir(dir_path):
    dir_file_path_list = [os.path.join(dir_path, file_name) for file_name in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file_name))]

    data = []
    for file in dir_file_path_list:
        with pdfplumber.open(file) as pdf:
            # Loop to identify the pages within a pdf and perform extractions on that page.
            for page in pdf.pages:
                text = page.extract_text()

                # String below indicates the page is the "dec page."
                if "THIS POLICY MEETS THE DEFINITION OF PRIVATE FLOOD INSURANCE" in text:
                    dec_page = text


                    # =============================== Bounding box of transaction type + policy number ===============================
                    x0, y0, x1, y1 = 190, 75, 405, 155
                    transaction_policy_number_bbox = (x0, y0, x1, y1)

                    transaction_policy_number_text = page.within_bbox(transaction_policy_number_bbox).extract_text()

                    start_marker = "Type:"
                    end_marker = "Transaction Effective Date:"

                    start_index = transaction_policy_number_text.find(start_marker)
                    end_index = transaction_policy_number_text.find(end_marker)

                    if start_index != -1 and end_index != -1:
                        # Extract the text between the markers
                        transaction_type, policy_number_text = transaction_policy_number_text[start_index + len(start_marker):end_index].strip().split('\n')

                        label, value = policy_number_text.strip().split(": ")
                        if "Policy Number" in label:
                            policy_number = value
                        if "New" in transaction_type:
                            transaction_type = "New Business"

                        print("Policy Number:", policy_number)
                        print("Transaction Type:", transaction_type)
                    else:
                        print("Could not identify markers!")


                    # =============================== Bounding box of name insured, mailing address ===============================
                    x0, y0, x1, y1 = 400, 144, 610, 264
                    name_insured_mailing_address_bbox = (x0, y0, x1, y1)

                    name_insured_mailing_address_text = page.within_bbox(name_insured_mailing_address_bbox).extract_text()

                    start_marker = "Named Insured(s):"
                    end_marker = "Mailing Address:"

                    start_index = name_insured_mailing_address_text.find(start_marker)
                    end_index = name_insured_mailing_address_text.find(end_marker)

                    if start_index != -1 and end_index != -1:
                        # Extract the text between the markers
                        name_insured = name_insured_mailing_address_text[start_index + len(start_marker):end_index].strip().replace("\n", " ")

                    doc = nlp(name_insured)

                    names = []
                    businesses = []
                    for entity in doc.ents:
                        if entity.label_ == "PERSON":  # Check if the entity is a person's name
                            names.append(entity.text.upper())
                        else:
                            businesses.append(entity.text.upper())

                    # Individual names will need reformatting if there are multiple last names.
                    if names:
                        grouped_names = {}
                        for name in names:
                            first_name, last_name = name.rsplit(' ', 1)
                            grouped_names.setdefault(last_name, []).append(first_name)

                        result = []
                        for last_name, first_names in grouped_names.items():
                            if len(first_names) == 1:
                                result.append(f"{first_names[0]} {last_name}")
                            else:
                                result.append(' & '.join(first_names) + f" {last_name}")
                        
                        result = " & ".join(result)
                        individual_insured = result

                    # Businesses will always be primary insured, individual names as secondary insured.
                    # If no business, then individual names are primary insured and secondary insured is None.
                    if businesses:
                        primary_insured = ' & '.join(businesses)
                        print("Primary Insured:", primary_insured)
                        if names:
                            secondary_insured = individual_insured
                            print("Secondary Insured:", secondary_insured)
                    else:
                        secondary_insured = None
                        primary_insured = individual_insured
                        print("Primary Insured:", primary_insured)
                        
                    mailing_address = name_insured_mailing_address_text[end_index + len(end_marker):].strip().replace("\n", " ").upper()

                    print("Mailing Address:", mailing_address)


                    # =============================== Bounding box of effective date, expiration date ===============================
                    x0, y0, x1, y1 = 0, 135, 320, 170
                    effective_date_bbox = (x0, y0, x1, y1)

                    effective_date_text = page.within_bbox(effective_date_bbox).extract_text()

                    start_marker = "Effective from"
                    end_marker = "both"

                    start_index = effective_date_text.find(start_marker)
                    end_index = effective_date_text.find(end_marker)

                    if start_index != -1 and end_index != -1:
                        # Extract the text between the markers
                        effective_date, expiration_date = effective_date_text[start_index + len(start_marker):end_index].strip().split(" to ")

                        # some documents have a trailing comma here: wrote this to catch it
                        if expiration_date[-1] == ',':
                            expiration_date = expiration_date[:-1]

                        # convert to datetime, then format to "MM/DD/YYYY"
                        effective_date = datetime.strptime(effective_date, "%m/%d/%Y")
                        effective_date = effective_date.strftime("%m/%d/%Y")
                        expiration_date = datetime.strptime(expiration_date, "%m/%d/%Y")
                        expiration_date = expiration_date.strftime("%m/%d/%Y")
                        
                        print("Effective Date: " + str(effective_date))
                        print("Expiration Date: " + str(expiration_date))


                    # =============================== Bounding box of insurer ===============================
                    x0, y0, x1, y1 = 0, 75, 193, 150
                    insurer_bbox = (x0, y0, x1, y1)

                    insurer_text = page.within_bbox(insurer_bbox).extract_text()

                    start_marker = "Insurance is effected with"
                    end_marker = "."

                    start_index = insurer_text.find(start_marker)
                    end_index = insurer_text.find(end_marker)

                    if start_index != -1 and end_index != -1:
                        # Extract the text between the markers
                        insurer = insurer_text[start_index + len(start_marker):end_index].strip().replace("\n", " ").upper()

                        print("Insurer:", insurer)


                    # =============================== Bounding box of premium + fees ===============================
                    x0, y0, x1, y1 = 335, 400, 612, 500
                    premium_bbox = (x0, y0, x1, y1)

                    premium_text = page.within_bbox(premium_bbox).extract_text()

                    start_marker = "Total Annual Premium"

                    start_index = premium_text.find(start_marker)

                    if start_index != -1:
                        # Extract the text between the markers
                        premiums = premium_text[start_index + len(start_marker):].strip().split('\n')

                        premium = 0.0
                        policy_fee = 0.0
                        sl_tax = 0.0
                        stamping_fee = 0.0
                        total_premium = 0.0

                        numeric_values = [float(re.search(r'\d+\.\d+', premium).group()) for premium in premiums]
                        premium = numeric_values[0]
                        policy_fee = numeric_values[1]
                        sl_tax = numeric_values[2]
                        stamping_fee = numeric_values[3]
                        total_premium = numeric_values[4]

                        print("Total Annual Premium:", premium)
                        print("Policy Fee:", policy_fee)
                        print("Surplus Lines Tax:", sl_tax)
                        print("Stamping Fee:", stamping_fee)
                        print("Total Policy Charges:", total_premium)
                        print()


                elif "CONFIDENTIAL REPORT OF SURPLUS LINE PLACEMENT" in text:
                    sl1 = text
                elif "DILIGENT SEARCH REPORT" in text:
                    sl2_page_1 = text
                elif "Was the risk described in Section 2" in text:
                    sl2_page_2 = text

                df = {
                    'policy-number': policy_number,
                    'primary-insured': primary_insured,
                    'secondary-insured': secondary_insured,
                    'mailing-address': mailing_address,
                    'transaction-type': transaction_type,
                    'insurer': insurer,
                    'effective-date': effective_date,
                    'expiration-date': expiration_date,
                    'premium': premium,
                    'policy-fee': policy_fee,
                    'sl-tax': sl_tax,
                    'stamping-fee': stamping_fee,
                    'total-premium': total_premium
                }

            data.append(df)

    dir_data = pd.DataFrame(data)

    return dir_data

def to_csv(df):
    # Set the path for the CSV file
    path = r'dir_data.csv'
    
    # Check if the path exists
    if os.path.exists(path):
        # Load the existing CSV into a dataframe
        existing_df = pd.read_csv(path)
        
        # Set policy-number as index for both dataframes
        existing_df.set_index('policy-number', inplace=True)
        df.set_index('policy-number', inplace=True)
        
        # Update values in existing_df based on policy-number
        existing_df.update(df)
        
        # Add new rows from df that are not present in existing_df
        existing_df = pd.concat([existing_df, df[~df.index.isin(existing_df.index)]])
        
        # Reset index for both dataframes
        existing_df.reset_index(inplace=True)
        df.reset_index(inplace=True)
        
        # Save the modified existing_df back to the CSV file
        existing_df.to_csv(path, index=False)
        
        print("CSV file updated successfully.")
    else:
        # If the path doesn't exist, save the entire input dataframe as a new CSV
        df.to_csv(path, index=False)
        print("CSV file created successfully.")
        
def main():
    flood_directory = r"Documents/Dallas Flood"
    df = extract_dir(flood_directory)
    to_csv(df)


main()
