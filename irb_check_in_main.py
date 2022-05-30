import os
import pandas as pd
os.chdir(os.path.dirname(__file__))
post_to_slack = pd.read_csv('zzz_post_to_slack.txt',header=None)[0][0]
post_to_traq = pd.read_csv('zzz_post_to_traq.txt',header=None)[0][0]
from irb_check_in_helper_functions import *
# ===============================================
# ===============================================
# get number of signed IRB waivers
total_waivers = get_number_of_completed_waivers(IRB_TEMPLATE_ID=IRB_TEMPLATE_ID, WAIVER_FOREVER_API_KEY=WAIVER_FOREVER_API_KEY)

# get the names of all athletes who have signed IRB waiver
athletes_with_signed_irb_waiver = get_names_with_signed_waiver(WAIVER_FOREVER_API_KEY, total_waivers)

# grab names of everyone who's mocapped in the past 30 days
pitchers_who_have_assessed_in_the_past_month, hitters_who_have_assessed_in_the_past_month = get_athletes_who_have_assessed_recently(creds_path, pitching_creds, hitting_creds, google_sheet_cols_pitching, google_sheet_cols_hitting, DAYS_TO_LOOK_BACK)

# compare lists of signed waivers with list of mocapped athletes
athletes_who_have_assessed_in_the_past_month = pd.concat([pitchers_who_have_assessed_in_the_past_month, hitters_who_have_assessed_in_the_past_month])
list_of_pitchers_who_have_not_signed_the_damn_waiver = list(set(list(pitchers_who_have_assessed_in_the_past_month['Athlete'])).difference(athletes_with_signed_irb_waiver)) # gets elements of list 2 that are not in list 1
list_of_hitters_who_have_not_signed_the_damn_waiver = list(set(list(hitters_who_have_assessed_in_the_past_month['Athlete'])).difference(athletes_with_signed_irb_waiver)) # gets elements of list 2 that are not in list 1

# calc proportion of mocapped athletes who have signed the waiver
compliance = 100*(1-(len(list_of_pitchers_who_have_not_signed_the_damn_waiver)+len(list_of_hitters_who_have_not_signed_the_damn_waiver))/len(athletes_who_have_assessed_in_the_past_month))
# prepare name + email dict for slack message
names_and_emails_pitchers = get_names_and_emails(list_of_pitchers_who_have_not_signed_the_damn_waiver, athletes_who_have_assessed_in_the_past_month)
names_and_emails_hitters = get_names_and_emails(list_of_hitters_who_have_not_signed_the_damn_waiver, athletes_who_have_assessed_in_the_past_month)

# compose message
message_header = ':rocket::rocket::rocket: *WEEKLY IRB COMPLIANCE CHECK-IN* :rocket::rocket::rocket:'
compliance_summary = f'*:chart_with_upwards_trend::chart_with_upwards_trend::chart_with_upwards_trend: ROLLING 30 DAY COMPLIANCE*: *_{np.int(compliance)}%_* :chart_with_upwards_trend::chart_with_upwards_trend::chart_with_upwards_trend:'
message_stem = '*Athletes over 18 who have mocaped recently but have not signed the IRB waiver*:'
message_footer_1 = '_workouts reminding them to stop at the front desk and fill out their paperwork have been added to their traq profiles_'
message_footer_2 = 'please make sure their waivers are filled out and accepted on _WaiverForever_ *_ASAP_*'
message_footer_3 = f'let {AT_WASS} know if you have any questions; many thanks :pray: '
message_footer_4 = f'{AT_TREY}\n{AT_ZACK}\n{AT_RHODESY}'
pitchers_list_ready_for_slack, pitcher_traq_ids = link_traq_profile(names_and_emails_pitchers, athletes_who_have_assessed_in_the_past_month)
hitters_list_ready_for_slack, hitter_traq_ids = link_traq_profile(names_and_emails_hitters, athletes_who_have_assessed_in_the_past_month)
pitchers_exist = len(names_and_emails_pitchers) != 0
hitters_exist = len(names_and_emails_hitters) != 0

if all([pitchers_exist, hitters_exist]):
    message_body = '\n\n' + f'*PITCHERS ({len(pitchers_list_ready_for_slack)})*:\n\n  - ' + '\n  - '.join(pitchers_list_ready_for_slack) + '\n\n' + f'*HITTERS ({len(hitters_list_ready_for_slack)})*: \n\n  - ' + '\n  - '.join(hitters_list_ready_for_slack)
elif all([pitchers_exist, hitters_exist]):
    message_body = "\n*_Nothing to report_*"
elif pitchers_exist:
    message_body = '\n\n' + f'*PITCHERS ({len(pitchers_list_ready_for_slack)})*:\n\n  - ' + '\n  - '.join(pitchers_list_ready_for_slack)
else:
    message_body = '\n\n' + f'*HITTERS ({len(hitters_list_ready_for_slack)})*: \n\n  - ' + '\n  - '.join(hitters_list_ready_for_slack)

if post_to_slack:
    if not all([pitchers_exist, hitters_exist]):
        client.postMessage(message_header +
        '\n\n' +
        compliance_summary +
        '\n\n' +
        message_stem +
        '\n' +
        message_body + 
        '\n\n' +
        message_footer_3 +
        '\n\n' +
        message_footer_4)
    else:
        client.postMessage(message_header +
        '\n\n' +
        compliance_summary +
        '\n\n' +
        message_stem +
        '\n' +
        message_body + 
        '\n\n' +
        message_footer_1 +
        '\n\n' +
        message_footer_2 + 
        '\n\n' + 
        message_footer_3 +
        '\n\n' +
        message_footer_4)
# post workout reminders in traq
if post_to_traq:
    for traq_id in pitcher_traq_ids+hitter_traq_ids:
        post_irb_reminder_to_traq(traq_id)
