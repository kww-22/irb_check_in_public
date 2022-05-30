import requests
from tqdm import tqdm
import pandas as pd
import numpy as np
from drivepy.traqapi import TraqAPI
from drivepy.slack import SlackAPI
from drivepy.digitaloceancluster import DigitalOceanCluster
import os
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime, timedelta
# ======================================================
# ======================================================
digital_ocean_host = os.environ['CLUSTER_HOST_DB_BIOMECH']
digital_ocean_username = os.environ['CLUSTER_USERNAME_DB_BIOMECH']
digital_ocean_password = os.environ['CLUSTER_PASSWORD_DB_BIOMECH']
digital_ocean_port = os.environ['CLUSTER_PORT_DB_BIOMECH']
digital_ocean_database = os.environ['DATABASE_THIRD_PARTY_API_DB']
WAIVER_FOREVER_API_KEY = os.environ['WAIVER_FOREVER_API_KEY'] # '7f8c054c8a1231b381101820f733febe'
IRB_TEMPLATE_TITLE = os.environ['IRB_TEMPLATE_TITLE'] # '18+ IRB Study Consent'
IRB_TEMPLATE_ID = os.environ['IRB_TEMPLATE_ID'] # 'MBxtLSRxBL1623804630'
HELP_CR_SLACK_ID = os.environ['HELP_CR_SLACK_ID'] # 'CBTQRRZ3K'
TEST_CHANNEL_SLACK_ID = os.environ['TEST_CHANNEL_SLACK_ID'] # 'C03H2Q4GDD3'
SLACK_BOT_JOHN_WICK_TOKEN = os.getenv("SLACK_BOT_JOHN_WICK_TOKEN")
# ======================================================
# ======================================================
digital_ocean_cluster = DigitalOceanCluster(digital_ocean_host, digital_ocean_username, digital_ocean_password, digital_ocean_port, digital_ocean_database)
traq_access_token = digital_ocean_cluster.getTraqAPIAccessToken()
traq_api = TraqAPI(traq_access_token)
client = SlackAPI(HELP_CR_SLACK_ID, SLACK_BOT_JOHN_WICK_TOKEN)
# dictionary to make querying WaiverForever's nested json easier
org_dict = {'single_choice_field':0,
'name_field_participant':1,
'email_field':2,
'date_field_participant':3,
'name_field_employee':4,
'date_field_employee':5}
creds_path = r"Y:\departments\research_and_development\sports_science\01_mocap_operations\supporting_files"
pitching_creds = "mocap-320519-93b6695fe619.json"
hitting_creds = "v1-hitting-tracking-sheet-1d0bf03d1130.json"
DAYS_TO_LOOK_BACK = 30
date_format = '%Y-%m-%d'
google_sheet_cols_pitching = ['Date', 'Athlete', 'Traq ID', 'Age', 'cat']
google_sheet_cols_hitting = ['Date', 'Name', 'Traq ID', 'Age', 'cat']
AT_WASS = '<@U01QZ1NL4K0>'
AT_TREY = '<@U02CPTUAX1T>'
AT_ZACK = '<@U02DJ9YJKFC>'
AT_RHODESY = '<@UJY12DQBD>'
# ======================================================
# ======================================================
# helper functions
def calculate_age(born, date_format=date_format):
    today = date.today()
    try:
        born = datetime.strptime(born, date_format)
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except:
        return np.nan

def link_traq_profile(names_and_emails, reference_df):
    base_traq_link = "https://traq.drivelinebaseball.com/athletes/view/"
    my_list, traq_ids = list(), list()
    for key, val in names_and_emails.items():
        traq_id = reference_df[reference_df['Athlete'] == key]['Traq ID'].iloc[0].lstrip('0')
        email = val
        my_list.append(f"<{base_traq_link}{traq_id}|{key}>   (:mailbox: {email})")
        traq_ids.append(traq_id)
    return my_list, traq_ids

def get_number_of_completed_waivers(IRB_TEMPLATE_ID, WAIVER_FOREVER_API_KEY):
    headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'X-Api-Key': WAIVER_FOREVER_API_KEY,
    }

    data = {
    'page': 1,
    'per_page': 10,
    'template_ids': [IRB_TEMPLATE_ID]
    }

    r = requests.post('https://api.waiverforever.com/openapi/v1/waiver/search', json=data, headers=headers)

    total_waivers = r.json()['data']['total']
    return total_waivers

def get_names_with_signed_waiver(WAIVER_FOREVER_API_KEY, TOTAL_NUMBER_OF_WAIVERS):
    athletes_with_signed_irb_waiver = list()
    for i in tqdm(range(TOTAL_NUMBER_OF_WAIVERS)):
        headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-Api-Key': WAIVER_FOREVER_API_KEY,
        }
        data = {
            'page': i,
            'per_page': 1,
            'template_ids': [IRB_TEMPLATE_ID]
            }
        r = requests.post('https://api.waiverforever.com/openapi/v1/waiver/search', json=data, headers=headers)
        name = r.json()['data']['waivers'][0]['data'][org_dict['name_field_participant']]['value']
        if name not in athletes_with_signed_irb_waiver:
            athletes_with_signed_irb_waiver.append(name)
        else:
            pass
    return athletes_with_signed_irb_waiver
    
def get_athletes_who_have_assessed_recently(creds_path, pitching_creds, hitting_creds, google_sheet_cols_pitching, google_sheet_cols_hitting, DAYS_TO_LOOK_BACK):
   # get hitters
   scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
   creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(creds_path, hitting_creds), scope)
   client = gspread.authorize(creds)
   sheet = client.open('v1 Hitting Master Athlete Info Sheet').get_worksheet_by_id(0)
   df = get_as_dataframe(sheet, evaluate_formulas=True, dtype = 'str').dropna(axis=0, how='all', subset=['Date', 'Swing_01']).dropna(axis=1, how='all').astype('str')
   df['Date'] = pd.to_datetime(df['Date'])
   df['cat'] = 'hitter'
   # df['Age'] = df['DOB'].apply(calculate_age)
   hitters_who_have_assessed_in_the_past_month = df[(df['Date'] >= date.strftime(date.today() - timedelta(days = DAYS_TO_LOOK_BACK),'%Y-%m-%d')) &
         (df['Date'] <= date.strftime(date.today() - timedelta(days = 2),'%Y-%m-%d')) &
      #    (df['Lab'] == 'DL - Kent') & 
         (df['Age'] >= '18') &
         (df['Level'] != 'milb') &
         (df['Level'] != 'mlb')][google_sheet_cols_hitting].reset_index().rename(columns={'index':'google_sheet_row','Name':'Athlete'})
   # get pitchers
   scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
   creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(creds_path, pitching_creds), scope)
   client = gspread.authorize(creds)
   sheet = client.open('V6 Master Athlete Info Sheet').get_worksheet_by_id(0)
   df = get_as_dataframe(sheet, evaluate_formulas=True, dtype = 'str').dropna(axis=0, how='all', subset=['Date', '_001']).dropna(axis=1, how='all').astype('str')
   df['Date'] = pd.to_datetime(df['Date'])
   df['Age'] = df['DOB'].apply(calculate_age)
   df['cat'] = 'pitcher'
   pitchers_who_have_assessed_in_the_past_month = df[(df['Date'] >= date.strftime(date.today() - timedelta(days = DAYS_TO_LOOK_BACK),'%Y-%m-%d')) &
         (df['Date'] <= date.strftime(date.today() - timedelta(days = 2),'%Y-%m-%d')) &
         (df['Lab'] == 'DL - Kent') & 
         (df['Age'] >= 18) &
         (df['Most Recent Level'] != 'milb') &
         (df['Most Recent Level'] != 'mlb')][google_sheet_cols_pitching].reset_index().rename(columns={'index':'google_sheet_row'})
   return pitchers_who_have_assessed_in_the_past_month, hitters_who_have_assessed_in_the_past_month

def post_irb_reminder_to_traq(traq_id):   
    bearer_token = 'Bearer ' + traq_access_token
    headers = {'content_type': 'multipart/form-data', 'Authorization': bearer_token}

    data = {
        'date': datetime.strftime(date.today() + timedelta(days = 1), '%Y-%m-%d'),
        'workout_id': 112445,
        'user_id': traq_id
    }
    try:
        r = requests.post("https://traq.drivelinebaseball.com/api/v1.1/add-athlete-workout", json=data, headers=headers)
        print(f"succefully added a reminder workout for traq profile {traq_id}")
    except:
        print(r.json())
        print('no workout posted')

def get_names_and_emails(list_of_names, reference_df):
    bearer_token = 'Bearer ' + traq_access_token
    headers = {'content_type': 'multipart/form-data', 'Authorization': bearer_token}
    names, emails, could_not_find_user, no_email = [], [], [], []
    for name in list_of_names:
        traq_id = reference_df[reference_df['Athlete'] == name]['Traq ID'].iloc[0].lstrip('0')
        if traq_id:
            data = {
                # 'name': name.split(" ")[0],
                # 'last_name': name.split(" ")[1]
                'id': traq_id
            }
            try:
                r = requests.get("https://traq.drivelinebaseball.com/api/v1.1/users", json=data, headers=headers)
            except:
                could_not_find_user.append(name)
            number_of_profiles = len(r.json()['data'])
            if number_of_profiles == 1:
                try:
                    emails.append(r.json()['data'][0]['email'])
                except:
                    emails.append("No email on file")
                    no_email.append(name)
            else:
                try:
                    emails.append(r.json()['data'][-1]['email']) # if there's more than one profile match, grab the email from the latest one
                except:
                    emails.append("No email on file")
                    no_email.append(name)
        else:
            emails.append("No email on file")
    names_and_emails = dict(zip(list_of_names, emails))
    return names_and_emails