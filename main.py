import os
import re
import pyautogui
import time
from random import choice, shuffle, randint
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException
from selenium.webdriver.support.select import Select

from config.personals import *
from modules.clickers_and_finders import *
from modules.openaiConnections import *
from config.secrets import use_AI, username, password, keywords, location
from modules.open_chrome import driver,actions   # your shared driver


keywords = "Software Engineer"
location = "United States"
useNewResume = True
aiClient = None
# Avoid applying to these companies if they have these bad words in their 'Job Description' section...  (In development)
bad_words = ["US Citizen","USA Citizen","No C2C", "No Corp2Corp", ".NET", "Embedded Programming", "PHP", "Ruby", "CNC"]  
re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)
first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name
desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary/12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

class JobApplyLinkedIn:
    LOGIN_URL   = "https://www.linkedin.com/login"
    JOBS_URL    = "https://www.linkedin.com/jobs/"
    WAIT_SECS   = 15                      # default explicit-wait timeout

    def __init__(self):
        self.email     = username
        self.password  = password
        self.keywords  = keywords
        self.location  = location
        self.driver    = driver
        self.wait      = WebDriverWait(self.driver, self.WAIT_SECS)

    # ---------- helpers ----------------------------------------------------

    def _wait(self, condition, timeout=None):
        """Shorthand for WebDriverWait"""
        return self.wait.until(condition) if timeout is None \
               else WebDriverWait(self.driver, timeout).until(condition)

    # ---------- main steps --------------------------------------------------

    def login(self, max_tries: int = 3):
        """Log in, retrying if we’re bounced back to the login page."""
        for attempt in range(1, max_tries + 1):
            self.driver.get(self.LOGIN_URL)

            # 1. user / password
            self._wait(EC.element_to_be_clickable((By.ID, "username"))).send_keys(
                self.email
            )
            pwd = self.driver.find_element(By.ID, "password")
            pwd.send_keys(self.password + Keys.RETURN)

            # 2. detect success (top-bar search box is a quick positive signal)
            try:
                self._wait(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[placeholder*='Search'][role='combobox']")
                    ),
                    timeout=8,
                )
                return  #logged in
            except TimeoutException:
                if attempt == max_tries:
                    raise RuntimeError("Couldn’t log in after 3 attempts.")

                print(f"Login attempt {attempt} failed; retrying …")
                time.sleep(2)  # short back-off and try again

    def search_jobs(self):
        """Jobs → fill keyword & location → choose suggestion / press Enter."""
        self.driver.get(self.JOBS_URL)

        # 1. keyword box
        kw_box = self._wait(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input.jobs-search-box__text-input[aria-label*='title']")
            )
        )
        kw_box.clear(); kw_box.send_keys(self.keywords)

        # 2. location box
        loc_box = self.driver.find_element(
            By.CSS_SELECTOR,
            "input.jobs-search-box__text-input[aria-label*='City']",
        )
        loc_box.clear(); loc_box.send_keys(self.location)

        # 3. choose suggestion if it appears, else press Enter
        try:
            suggestion = self._wait(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//ul[contains(@class,'jobs-search-box__autocomplete-list')]"
                        f"//li//span[normalize-space(text())='{self.location}']",
                    )
                ),
                timeout=3,
            )
            suggestion.click()
        except TimeoutException:
            loc_box.send_keys(Keys.RETURN)

        # 4. wait for result list
        time.sleep(5)

    # -----------------------------------------------------------------------
    def apply_easy_apply_filter(self):
        """Click the Easy Apply pill directly using its stable id attribute."""
        try:
            # locate quickly by ID (stable as of 2025‑04)
            btn = self._wait(
                EC.presence_of_element_located((By.ID, "searchFilter_applyWithLinkedin")),
                timeout=5,
            )
            # ensure it is clickable – scroll into view, wait, then JS‑click fallback
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            self._wait(EC.element_to_be_clickable((By.ID, "searchFilter_applyWithLinkedin")), timeout=5)
            try:
                btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", btn)
            print(" Easy Apply pill clicked.")
        except TimeoutException:
            print(" Easy Apply pill not found – skipping filter.")
    

    # Function to discard the job application
    def discard_job(self):
        actions.send_keys(Keys.ESCAPE).perform()
        wait_span_click(driver, 'Discard', 2)

    def extract_years_of_experience(text: str) -> int:
        # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
        matches = re.findall(re_experience, text)
        if len(matches) == 0: 
            print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
            return 0
        return max([int(match) for match in matches if int(match) <= 12])

    def get_job_main_details(self,job: WebElement) -> tuple[str, str, str, str, str, bool]:
        '''
        # Function to get job main details.
        Returns a tuple of (job_id, title, company, work_location, work_style, skip)
        * job_id: Job ID
        * title: Job title
        * company: Company name
        * work_location: Work location of this job
        * work_style: Work style of this job (Remote, On-site, Hybrid)
        * skip: A boolean flag to skip this job
        '''
        job_details_button = job.find_element(By.TAG_NAME, 'a') # job_details_button = job.find_element(By.CLASS_NAME, "job-card-list__title")  # Problem in India
        scroll_to_view(driver, job_details_button, True)
        job_id = job.get_dom_attribute('data-occludable-job-id')
        title = job_details_button.text
        title = title[:title.find("\n")]
        # company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
        # work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
        other_details = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
        index = other_details.find(' · ')
        company = other_details[:index]
        work_location = other_details[index+3:]
        work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
        work_location = work_location[:work_location.rfind('(')].strip()
        
        # Skip if previously rejected due to blacklist or already applied
        skip = False

        try:
            if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
                skip = True
                print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
        except: pass
        try: 
            if not skip: job_details_button.click()
        except Exception as e:
            print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!') 
            # print_lg(e)
            self.discard_job()
            job_details_button.click() # To pass the error outside
        buffer(click_gap)
        return (job_id,title,company,work_location,work_style,skip)

    def apply_to_jobs(self):
        try:
            # Wait until job listings are loaded
            self._wait(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))
            # Find all job listings in current page
            buffer(5)      
            job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")  
               
            for job in job_listings:
                pyautogui.press('shiftright')
                print_lg("\n-@-\n")

                job_id,title,company,work_location,work_style,skip = self.get_job_main_details(job)             
               
                description, experience_required, skip, reason, message = self.get_job_description()

                if description != "Unknown" and use_AI:
                        skills = ai_extract_skills(aiClient, description)
                else:
                        skills = "Unknown"

                if use_AI and description != "Unknown":
                    should_apply = ai_check_job_relevance(
                    aiClient,
                    job_title=title,
                    company=company,
                    location=work_location,
                    work_style=work_style,
                    experience_required=experience_required,
                    job_skills=skills,
                    job_description=description
                     )
                # should_apply = True # Enable for Testing...........    
                if not should_apply:
                    print_lg(f"=======================\nJob does not match with your resume as per AI model ⇒ – skipping {title} | {company}\n================================")
                    continue
                
                if should_apply:
                    print_lg("=================================\nApplying for Job now....\n========================================")
                easy_apply_button = self._wait(
                        EC.element_to_be_clickable((By.ID, "jobs-apply-button-id"))
                    )
                easy_apply_button.click()
                buffer(1)
                try:
                    self.submitJobs(work_location=work_location,description=description)
                except Exception as e:
                    print_lg("Failed to Easy apply!")
                    critical_error_log("Somewhere in Easy Apply process",e)
                    self.discard_job()
                    continue            

        except Exception as e:
            print_lg("Failed to find Job listings!")     

    def upload_resume(self, modal: WebElement, resume_path: str) -> tuple[bool,str]:
        abs_path = os.path.abspath(resume_path)
        if not os.path.exists(abs_path):
            print(f"[ERROR] Resume not found at {abs_path}")
            return False, None
        try:
            input_file = modal.find_element(By.CSS_SELECTOR, "input[type='file']")
            input_file.send_keys(abs_path)
            print(f"[OK] Uploaded resume from {abs_path}")
            return True, os.path.basename(abs_path)
        except Exception as e:
            print(f"[ERROR] upload_resume failed: {e}")
            return False, None

    def submitJobs(self,work_location:str,description:str):
                            try:
                                uploaded=False
                                errored = ""
                                modal = find_by_class(driver, "jobs-easy-apply-modal")
                                wait_span_click(modal, "Next", 1)
                                # if description != "Unknown":
                                #     resume = create_custom_resume(description)
                                next_button = True
                                questions_list = set()
                                next_counter = 0
                                while next_button:
                                    next_counter += 1
                                    if next_counter >= 15: 
                                        if pause_at_failed_question:
                                            pyautogui.alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                            next_counter = 1
                                            continue
                                        if questions_list: print_lg("Stuck for one or some of the following questions...", questions_list)
                                        errored = "stuck"
                                        raise Exception("Seems like stuck in a continuous loop of next, probably because of new questions.")
                                    questions_list = self.answer_questions(modal, questions_list, work_location, job_description=description)
                                    if useNewResume and not uploaded: uploaded, resume = self.upload_resume(modal, default_resume_path)
                                    try: next_button = modal.find_element(By.XPATH, './/span[normalize-space(.)="Review"]') 
                                    except NoSuchElementException:  next_button = modal.find_element(By.XPATH, './/button[contains(span, "Next")]')
                                    try: next_button.click()
                                    except ElementClickInterceptedException: break    # Happens when it tries to click Next button in About Company photos section
                                    buffer(click_gap)
                            except NoSuchElementException: errored = "nose"
                            finally:
                                if questions_list and errored != "stuck": 
                                    print_lg("Answered the following questions...", questions_list)
                                    print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")
                                print_lg("This project is just to a poc i am not going to submit or apply for any job, move to next")
                                

    def answer_common_questions(self,label: str, answer: str) -> str:
        if 'sponsorship' in label or 'visa' in label: answer = require_visa
        return answer
    
    # Function to answer the questions for Easy Apply
    def answer_questions(self,modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> set:
        # Get all questions from the page
        
        all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
        # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
        # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
        # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
        # all_questions = all_questions + all_list_questions + all_single_line_questions

        for Question in all_questions:
            # Check if it's a select Question
            select = try_xp(Question, ".//select", False)
            if select:
                label_org = "Unknown"
                try:
                    label = Question.find_element(By.TAG_NAME, "label")
                    label_org = label.find_element(By.TAG_NAME, "span").text
                except: pass
                answer = 'Yes'
                label = label_org.lower()
                select = Select(select)
                selected_option = select.first_selected_option.text
                optionsText = []
                options = '"List of phone country codes"'
                if label != "phone country code":
                    optionsText = [option.text for option in select.options]
                    options = "".join([f' "{option}",' for option in optionsText])
                prev_answer = selected_option
                if overwrite_previous_answers or selected_option == "Select an option":
                    if 'email' in label or 'phone' in label: answer = prev_answer
                    elif 'gender' in label or 'sex' in label: answer = gender
                    elif 'disability' in label: answer = disability_status
                    elif 'proficiency' in label: answer = 'Professional'
                    else: answer = self.answer_common_questions(label,answer)
                    try: select.select_by_visible_text(answer)
                    except NoSuchElementException as e:
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer == 'Decline' else [answer]
                        foundOption = False
                        for phrase in possible_answer_phrases:
                            for option in optionsText:
                                if phrase in option:
                                    select.select_by_visible_text(option)
                                    answer = f'Decline ({option})' if len(possible_answer_phrases) > 1 else option
                                    foundOption = True
                                    break
                            if foundOption: break
                        if not foundOption:
                            #TODO: Use AI to answer the question need to be implemented logic to extract the options for the question
                            print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')
                            select.select_by_index(randint(1, len(select.options)-1))
                            answer = select.first_selected_option.text
                questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
                continue
            
            # Check if it's a radio Question
            radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
            if radio:
                prev_answer = None
                label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
                try: label = find_by_class(label, "visually-hidden", 2.0)
                except: pass
                label_org = label.text if label else "Unknown"
                answer = 'Yes'
                label = label_org.lower()

                label_org += ' [ '
                options = radio.find_elements(By.TAG_NAME, 'input')
                options_labels = []
                
                for option in options:
                    id = option.get_attribute("id")
                    option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                    options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                    if option.is_selected(): prev_answer = options_labels[-1]
                    label_org += f' {options_labels[-1]},'

                if overwrite_previous_answers or prev_answer is None:
                    if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                    elif 'veteran' in label or 'protected' in label: answer = veteran_status
                    elif 'disability' in label or 'handicapped' in label: 
                        answer = disability_status
                    else: answer = self.answer_common_questions(label,answer)
                    foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                    if foundOption: 
                        actions.move_to_element(foundOption).click().perform()
                    else:    
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer == 'Decline' else [answer]
                        ele = options[0]
                        answer = options_labels[0]
                        for phrase in possible_answer_phrases:
                            for i, option_label in enumerate(options_labels):
                                if phrase in option_label:
                                    foundOption = options[i]
                                    ele = foundOption
                                    answer = f'Decline ({option_label})' if len(possible_answer_phrases) > 1 else option_label
                                    break
                            if foundOption: break
                        # if answer == 'Decline':
                        #     answer = options_labels[0]
                        #     for phrase in ["Prefer not", "not want", "not wish"]:
                        #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                        #         if foundOption:
                        #             answer = f'Decline ({phrase})'
                        #             ele = foundOption
                        #             break
                        actions.move_to_element(ele).click().perform()
                else: answer = prev_answer
                questions_list.add((label_org+" ]", answer, "radio", prev_answer))
                continue
            
            # Check if it's a text question
            text = try_xp(Question, ".//input[@type='text']", False)
            if text: 
                do_actions = False
                label = try_xp(Question, ".//label[@for]", False)
                try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
                except: pass
                label_org = label.text if label else "Unknown"
                answer = "" # years_of_experience
                label = label_org.lower()

                prev_answer = text.get_attribute("value")
                if not prev_answer or overwrite_previous_answers:
                    if 'experience' in label or 'years' in label: answer = years_of_experience
                    elif 'phone' in label or 'mobile' in label: answer = phone_number
                    elif 'street' in label: answer = street
                    elif 'city' in label or 'location' in label or 'address' in label:
                        answer = current_city if current_city else work_location
                        do_actions = True
                    elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                    elif 'name' in label:
                        if 'full' in label: answer = full_name
                        elif 'first' in label and 'last' not in label: answer = first_name
                        elif 'middle' in label and 'last' not in label: answer = middle_name
                        elif 'last' in label and 'first' not in label: answer = last_name
                        elif 'employer' in label: answer = recent_employer
                        else: answer = full_name
                    elif 'notice' in label:
                        if 'month' in label:
                            answer = notice_period_months
                        elif 'week' in label:
                            answer = notice_period_weeks
                        else: answer = notice_period
                    elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label: 
                        if 'current' in label or 'present' in label:
                            if 'month' in label:
                                answer = current_ctc_monthly
                            elif 'lakh' in label:
                                answer = current_ctc_lakhs
                            else:
                                answer = current_ctc
                        else:
                            if 'month' in label:
                                answer = desired_salary_monthly
                            elif 'lakh' in label:
                                answer = desired_salary_lakhs
                            else:
                                answer = desired_salary
                    elif 'linkedin' in label: answer = linkedIn
                    elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                    elif 'scale of 1-10' in label: answer = confidence_level
                    elif 'headline' in label: answer = linkedin_headline
                    elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "https://github.com/GodsScion/Auto_job_applier_linkedIn"
                    elif 'state' in label or 'province' in label: answer = state
                    elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                    elif 'country' in label: answer = country
                    else: answer = self.answer_common_questions(label,answer)
                    if answer == "":
                        if use_AI and aiClient:
                            try:
                                answer = ai_answer_question(aiClient, label_org, question_type="text" ,job_description=job_description, user_information_all = user_information_all)
                                print_lg(f'AI Answered recived for question"{label_org}" \nhere is answer : "{answer}"')
                            except Exception as e:
                                print_lg("Failed to get AI answer!", e)
                        else:
                            answer = years_of_experience
                    ##<   
                    text.clear()
                    text.send_keys(answer)
                    if do_actions:
                        sleep(2)
                        actions.send_keys(Keys.ARROW_DOWN)
                        actions.send_keys(Keys.ENTER).perform()
                questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
                continue

            # Check if it's a textarea question
            text_area = try_xp(Question, ".//textarea", False)
            if text_area:
                label = try_xp(Question, ".//label[@for]", False)
                label_org = label.text if label else "Unknown"
                label = label_org.lower()
                answer = ""
                prev_answer = text_area.get_attribute("value")
                if not prev_answer or overwrite_previous_answers:
                    if 'summary' in label: answer = linkedin_summary
                    elif 'cover' in label: answer = cover_letter
                    if answer == "":
                        if use_AI and aiClient:
                            try:
                                answer = ai_answer_question(aiClient, label_org, question_type="textarea" ,job_description=job_description, user_information_all = user_information_all)
                                print_lg(f'AI Answered recived for question"{label_org}" \nhere is answer : "{answer}"')
                            except Exception as e:
                                print_lg("Failed to get AI answer!", e)
                        else:
                            print("randomly answered question")
                text_area.clear()
                text_area.send_keys(answer)
                if do_actions:
                        sleep(2)
                        actions.send_keys(Keys.ARROW_DOWN)
                        actions.send_keys(Keys.ENTER).perform()
                questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
                ##<
                continue

            # Check if it's a checkbox question
            checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
            if checkbox:
                label = try_xp(Question, ".//span[@class='visually-hidden']", False)
                label_org = label.text if label else "Unknown"
                label = label_org.lower()
                answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
                answer = answer.text if answer else "Unknown"
                prev_answer = checkbox.is_selected()
                checked = prev_answer
                if not prev_answer:
                    try:
                        actions.move_to_element(checkbox).click().perform()
                        checked = True
                    except Exception as e: 
                        print_lg("Checkbox click failed!", e)
                        pass
                questions_list.add((f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
                continue


        # Select todays date
        try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

        # Collect important skills
        # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
        # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

        return questions_list

    def get_job_description(self) -> tuple[
        str | Literal['Unknown'],
        int | Literal['Unknown'],
        bool,
        str | None,
        str | None
        ]:
        '''
        # Job Description
        Function to extract job description from About the Job.
        ### Returns:
        - `jobDescription: str | 'Unknown'`
        - `experience_required: int | 'Unknown'`
        - `skip: bool`
        - `skipReason: str | None`
        - `skipMessage: str | None`
        '''
        try:
            jobDescription = "Unknown"
            experience_required = "Unknown"
            jobDescription = find_by_class(driver, "jobs-box__html-content").text
            jobDescriptionLow = jobDescription.lower()
            current_experience = years_of_experience
            skip = False
            skipReason = None
            skipMessage = None
            for word in bad_words:
                if word.lower() in jobDescriptionLow:
                    skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                    skipReason = "Found a Bad Word in About Job"
                    skip = True
                    break
            if not skip and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
                skipMessage = f'\n{jobDescription}\n\nFound "Clearance" or "Polygraph". Skipping this job!\n'
                skipReason = "Asking for Security clearance"
                skip = True
            if not skip:
                experience_required = self.extract_years_of_experience(jobDescription)
                if current_experience > -1 and experience_required > current_experience:
                    skipMessage = f'\n{jobDescription}\n\nExperience required {experience_required} > Current Experience {current_experience}. Skipping this job!\n'
                    skipReason = "Required experience is high"
                    skip = True
        except Exception as e:
            if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
            else:
                experience_required = "Error in extraction"
                print_lg("Unable to extract years of experience required!")
                # print_lg(e)
        finally:
            return jobDescription, experience_required, skip, skipReason, skipMessage
        
   
    def testOpenAi(self):
                title= "Sr. iOS Mobile Application Developer (Hybrid)"
                company= "Redolent, In"
                work_location= "dolent, In"
                work_style= "dolent, In"
                experience_required= "Error in extraction"
                description= "We are seeking a highly skilled and experienced Senior iOS Mobile Application Developer to join our dynamic team on a hybrid contract basis. The ideal candidate will have deep expertise in Swift, UIKit, SwiftUI, and a strong grasp of modern iOS architecture patterns. You will play a key role in the design, development, and enhancement of iOS mobile applications that power delightful, intuitive, and secure user experiences."+"Responsibilities:"+"Design, develop, and maintain advanced iOS applications using Swift, SwiftUI, and UIKit."+"Collaborate with cross-functional teams including product managers, designers, QA engineers, and backend developers to define, design, and ship new features."+"Optimize application performance and memory management to ensure high-quality user experiences."+"Write clean, scalable, maintainable code and participate in code reviews."+"Integrate RESTful APIs and third-party libraries."
                
                if description != "Unknown" and use_AI:
                        print("ai extract skills is called")
                        skills = ai_extract_skills(aiClient, description)
                else:
                        skills = "Unknown"

                if use_AI and description != "Unknown":
                    print("ai_check_job_relevance is called")
                    should_apply = ai_check_job_relevance(
                    aiClient,
                    job_title=title,
                    company=company,
                    location=work_location,
                    work_style=work_style,
                    experience_required=experience_required,
                    job_skills=skills,
                    job_description=description
                     )
                if not should_apply:
                    print_lg(f"GPT ⇒ NO – skipping {title} | {company}")
                
                print(
                    "Job Title:", title,
                    "\nCompany:", company,
                    "\nLocation:", work_location,
                    "\nWork Style:", work_style,
                    "\nExperience Required:", experience_required,
                    "\nJob Skills:", skills,
                    "\nJob Description:", description
                )
                print(should_apply)

    def run(self):
        try:
            global  useNewResume, aiClient
            resume_path = os.path.abspath(default_resume_path)
            if not os.path.exists(resume_path):
                pyautogui.alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format("resume/resume.pdf"), title="Missing Resume", button="OK")
                useNewResume = False


            if use_AI:
                aiClient = ai_create_openai_client()
            
            self.login()
            self.search_jobs()
            self.apply_easy_apply_filter()
            buffer(1)
            self.apply_to_jobs()
            # self.testOpenAi()
        except NoSuchWindowException:   pass
        except Exception as e:
            critical_error_log("In Applier Main", e)
            pyautogui.alert(e)
        finally:
            print_lg("Closing the browser...")
            ai_close_openai_client(aiClient)
            try: driver.quit()
            except Exception as e: critical_error_log("When quitting...", e)

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    bot = JobApplyLinkedIn()
    bot.run()