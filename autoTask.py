import sys
import os
import time
import pytz
import pickle
import gspread
import json
from datetime import datetime
from google.oauth2 import service_account 
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from google.auth.transport.requests import Request

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

local_tz = pytz.timezone("Asia/Ho_Chi_Minh")
GOOGLE_CLIENT_SECRET = "auto\client_secret.json"
TOKEN_PICKLE = "token.pickle"
GIAO_TASK_SHEET_URL = ""

USERNAME = ""
PASSWORD = ""

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

group_names = {
    "iX000s iSSale Boom QT*iHugeNewRev*Top-iUp": "gr_qt",
    "BoomWTF..AiLàmViệcRiêng*ThựcNÃO*ProofFileNGAY": "gr_boom",
    "iX000s iSSale AH GlobalGroup.NỆN*iHugeNewRev*TiUp": "gr_iX000s",
    "iX000s iSSale Boom&Task_1h TTS AA POSITIVE iShowOff/Top-iUp": "gr_iShowOff",
    "iX000s iSSale Boom CMT*iHugeNewRev*Top-iUp": "gr_iHugeNewRev",
    "iX000s iSSale AU GlobalGroup.NỆN*iHugeNewRev*TiUp": "gr_GlobalGroup",
    "Satakunta SAM":"ss_dm",
    "test group":"gr_test"
}

# ========== Google OAuth ==========
def authenticate_google():
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CLIENT_SECRET, 
            scopes=SCOPES
        )
        print("✅ Xác thực thành công bằng Service Account.")
        return creds
        
    except Exception as e:
        print(f"❌ Lỗi xác thực Service Account: {e}")
        print("💡 Đảm bảo file client_secret.json là key của Service Account và đã cấp quyền cho Sheet.")
        raise


# mở trang google sheets
def open_sheet(creds):
    return gspread.authorize(creds)

#Lấy data từ google sheets
def get_task_data(creds):
    EXPECTED_HEADERS =[
        "Task", "File note", "Người làm", "Nhóm gửi", "Trạng thái", "Display Name"
    ]
    sheet = open_sheet(creds).open_by_url(GIAO_TASK_SHEET_URL).sheet1
    raw = sheet.get_all_records(expected_headers=EXPECTED_HEADERS)
    rows = [{k.strip().lower(): v for k, v in row.items()} for row in raw]
    return sheet, rows

#Lấy link từ dòng file note
def get_user_sheet_url(row):
    url = row.get("file note", "").strip()
    return url if url.startswith("https://docs.google.com") else None

#Kiểm tra task đã gửi hay chưa
def is_task_sent(row):
    status = str(row.get("trạng thái", "")).strip().lower()
    #print(f"DEBUG: Status for row: '{status}'")  # Log the exact status
    return status in ["đã gửi", "x", "yes"]

#Lấy dữ liệu của một cột trong google sheets
def get_col_index(sheet, col_name):
    headers = sheet.row_values(1)
    for idx, header in enumerate(headers):
        if header.strip().lower() == col_name.strip().lower():
            return idx + 1
    raise Exception(f"Không tìm thấy cột '{col_name}' trong Sheet.")


def append_to_user_sheet(creds, sheet_url, task):
    sheet = open_sheet(creds).open_by_url(sheet_url).sheet1
    if "\n" in task:
        first_line, full = task.split("\n", 1)
    else:
        first_line, full = task, task
    sheet.append_row([first_line.strip(), task.strip()])

# ================driver setup ==================
def get_driver():

    ## đường dẫn dến file chromedriver.exe 
    chromedriver_path = "chromedriver-win64\chromedriver.exe"

    options = Options()
    # options.add_argument("--headless")  # Chỉ bật khi chạy ngầm
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 11.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        },
    )
    return driver

#Mở chrome và đăng nhập vào msteam
def login_teams(driver):
    driver.get("https://login.microsoftonline.com/")

    try:
        # Nhập email
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "loginfmt"))
        ).send_keys(USERNAME + Keys.RETURN)
        time.sleep(2)

        #Xử lý trang "verify your email"
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/div/div/div/div[1]/div/div/div/div/form/div[2]/div/span[2]/div/span"))
            ).click()
        except:
            print("⚠️ Could not find 'Stay signed in' prompt, continuing...")   

        # Nhập mật khẩu
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "passwd"))
        ).send_keys(PASSWORD + Keys.RETURN)
        time.sleep(2)

        # Xử lý "Stay signed in?"
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='No']"))
            ).click()
        except:
            print("⚠️ Could not find 'Stay signed in' prompt, continuing...")

        # Chuyển đến trang Microsoft Teams sau login
        driver.get("https://teams.microsoft.com/")
        time.sleep(5)

        # Chờ giao diện chính sẵn sàng
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="textbox" or @contenteditable="true"]'))
        )
        print("✅ Successfully logged in to Microsoft Teams.")

    except Exception as e:
        print(f"❌ Login failed: {e}")
        driver.save_screenshot("teams_login_failed.png")
        raise

#===============function========================
def search_chat(driver, ms_email):
    # Sử dụng XPath tương đối cho thanh tìm kiếm
    search_bar_xpath = '//*[@id="ms-searchux-input"]'
    
    # XPath tương đối tìm kiếm một người dùng cụ thể bằng email
    # Teams thường hiển thị email/tên trong một div/span có thuộc tính cố định.
    # Chúng ta tìm kiếm kết quả đầu tiên (div có role='option') nằm dưới tiêu đề 'People'
    first_result_xpath_relative = (
        "//div[@role='listbox']" # Khung chứa kết quả
        "//div[@id='heading_PEOPLE' and contains(text(), 'People')]" # Tìm tiêu đề 'People'
        "/following-sibling::div[1]" # Lấy div ngay sau tiêu đề People
        "//div[@role='option']" # Lấy kết quả đầu tiên trong nhóm People
    )
    
    try:
        ms = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, search_bar_xpath))
        )
        ms.send_keys(ms_email)
        time.sleep(10) # Tăng thời gian chờ để kết quả tìm kiếm tải xong

        # Tìm và click vào kết quả đầu tiên trong nhóm 'People'
        first_result = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, first_result_xpath_relative))
        )
        
        # Thử click và dùng JS Click dự phòng (giống như logic bạn đã dùng trước đó)
        try:
            first_result.click()
        except Exception:
            driver.execute_script("arguments[0].click();", first_result)
            
        time.sleep(3)
        print(f"✅ Đã chọn kết quả tìm kiếm (People) cho: {ms_email}")
        return True
        
    except Exception as e:
        print(f"❌ Không tìm thấy người dùng hoặc lỗi click cho: {ms_email}. Chi tiết: {e}")
        return False
    
#Tìm thêm chat ---> có lỗi về phần first_result do có thêm dòng people (người quen hay đã có chat với người đó)
def open_chat(driver, chat_name):
    search_xpath = f"//span[contains(text(), '{chat_name}')]"
    try:
        chat = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, search_xpath))
        )
        chat.click()
        time.sleep(3)
        return True
    except Exception:
        print(f"❌ Không tìm thấy nhóm chat: {chat_name}")
        return False

def send_message(driver, message):
    msg_box = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]')))
    msg_box.send_keys(message)
    msg_box.send_keys(Keys.ENTER)

def process_tasks(driver, creds):
    try:    
        sheet, tasks = get_task_data(creds)
        #print(f"DEBUG: Loaded {len(tasks)} rows")

        task_status = [is_task_sent(row) for row in tasks] #kiểm tra task_status là False hay true
        #print(f"DEBUG: Task statuses: {task_status}")

        if all(task_status):# nếu task_status là all true thì thoát
            print(f"✅ Tất cả task trong sheet đã được đánh dấu 'Đã gửi'. Thoát chương trình xử lý task.")
            #driver.quit()
            #sys.exit()
            return driver.quit() #dùng để đóng trình duyệt và chức năng

        print (f"🔔 Vẫn còn task CHƯA ĐƯỢC GỬI. Bắt đầu xử lý...")
    except Exception as e:
        print(f"error loading :{e}")
        driver.quit()
        return

    for i, row in enumerate(tasks):
        if is_task_sent(row):
            continue

        try:
            task = row["task"]
            file_note = row["file note"]
            intern = row["người làm"].replace("@", "").strip()
            group = row["display name"]
            email = row["email"]

            #Kiểm tra nhóm gửi và email trong file google sheets
            if not group and not email:
                print(f'❌ Dòng {i+2} không tìm thấy nhóm gửi và email cho {intern}')
                continue


            if not file_note or not isinstance(file_note, str) or not file_note.startswith("http"):
                print(f"❌ Dòng {i+2} không tìm thấy sheet cá nhân trong File Note cho {intern}")
                continue

            message = f"Đây là test run @Satakunta SAM; @{intern} - Bạn có task mới:\n{task} -File note:"
            message1 = f"{file_note}"
            
            chat_opened = False

            if email and isinstance(email, str) and '@' in email:
                if search_chat(driver, email):
                    chat_opened=True 
                
            if not chat_opened and group:
                if open_chat(driver, group):
                    chat_opened = True


            if not chat_opened:
                print(f"❌ Không tìm thấy nhóm chat: {group}")
                continue

            send_message(driver, message)
            send_message(driver, message1)

            try:
                append_to_user_sheet(creds, file_note, task)
            except Exception as e:
                print(f"⚠️ Gửi được task nhưng không ghi được vào sheet cá nhân của {intern}: {e}")

            try:# cập nhập trạng thái gửi ở file google sheets
                col_idx = get_col_index(sheet, "Trạng thái")
                sheet.update_cell(i + 2, col_idx, "Đã gửi")
            except Exception as e:
                print(f"⚠️ Không thể cập nhật trạng thái gửi trong sheet chính: {e}")

            print(f"✅ Đã gửi task cho {intern}")

        except Exception as e:
            print(f"❌ Lỗi dòng {i+2}: {e}")

# ========== Main ==========
if __name__ == "__main__":
    try:
        creds = authenticate_google()
        driver = get_driver()
        try:
            login_teams(driver)
            process_tasks(driver, creds)
            print(f"✅ Đã chạy thành công")
        finally:
            driver.quit()
    except Exception as e:
        print(f"❌ Chạy không thành công và lỗi {e}")
