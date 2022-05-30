**AUTOMATED IRB WAIVER CHECK IN BOT**

author: Kyle Wasserberger

first pushed: 2022-05-27

adaped for public view from my internal Driveline repo (sensitive information redacted)

*purpose*:

python script to scrape WaiverForever + Traq + mocap collection googlesheet to determine which athletes over 18 years old who've mocapped in the last 30 days have **NOT** signed the IRB waiver

irb_check_in_helper_functions.py
- python file with functions to streamline main script's code

irb_check_in_main.py
- actual script that does all the scraping, slack pinging, and traq workout posting

---

**SUMMARIZED WORKFLOW**

1. scrape WaiverForever for list of athlete names who have completed 18+ IRB Study Waiver
2. scrape current pitching & hitting mocap collection googlesheets for names of athletes who have assessed (currently filtered to last 30 days)
3. compare list of signed waivers with list of mocapped athletes
4. post workout to traq profile of athlete's who have not filled out waiver
5. ping #help-cr with list of athlete names + emails who have not filled out waiver

