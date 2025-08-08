# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 12:55:59 2025

@author: SE15111
"""
import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import calendar
import os
import time # Add time module for delays between requests

from dotenv import load_dotenv
load_dotenv()


# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebScraper:
    def __init__(self):
        """
        Initializes the WebScraper with a session and disables SSL verification.
        Also loads Telegram bot and user credentials from environment variables.
        """
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL certificate verification
        
        # Telegram Bot Token and Chat ID from environment variables
        # IMPORTANT: These MUST be set as GitHub Secrets for security.
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

        # User credentials from environment variables
        # IMPORTANT: These MUST be set as GitHub Secrets for security.
        # Default values are for local testing ONLY and should NOT be hardcoded in production.
        self.mb_id = os.getenv('MB_ID') 
        self.mb_password = os.getenv('MB_PASSWORD') 

        # Basic validation for credentials
        if not self.mb_id or not self.mb_password:
            print("Error: MB_ID or MB_PASSWORD environment variables are not set.")
            # In a real scenario, you might want to exit here or raise an exception.
            # For now, we'll proceed but login will likely fail.
        
    def send_telegram_message(self, message):
        """
        Sends a message to a Telegram chat using the configured bot token and chat ID.
        Messages are sent in HTML parse mode for basic formatting.
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram bot token or chat ID not set. Skipping Telegram notification.")
            return

        telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML' # Use HTML for basic formatting like bold
        }
        try:
            response = requests.post(telegram_url, json=payload)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            print(f"Telegram message sent: {message}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send Telegram message: {e}")
    
    def get_first_weekday_of_month(self, year, month, weekday):
        """
        Finds the first occurrence of a specific weekday in a given month and year.
        
        Args:
            year (int): The year.
            month (int): The month (1-12).
            weekday (int): The weekday (0=Monday, 6=Sunday).
            
        Returns:
            str: The date in 'YYYY-MM-DD' format.
        """
        first_day = datetime(year, month, 1)
        first_weekday = first_day.weekday()
        
        # Calculate days ahead to reach the first target weekday
        days_ahead = weekday - first_weekday
        if days_ahead < 0:
            days_ahead += 7
            
        target_date = first_day + timedelta(days=days_ahead)
        return target_date.strftime('%Y-%m-%d')
    
    def get_last_weekday_of_month(self, year, month, weekday):
        """
        Finds the last occurrence of a specific weekday in a given month and year.
        
        Args:
            year (int): The year.
            month (int): The month (1-12).
            weekday (int): The weekday (0=Monday, 6=Sunday).
            
        Returns:
            str: The date in 'YYYY-MM-DD' format.
        """
        # Get the last day of the month
        last_day = datetime(year, month, calendar.monthrange(year, month)[1])
        
        # Calculate days back to reach the last target weekday
        days_back = (last_day.weekday() - weekday) % 7
        target_date = last_day - timedelta(days=days_back)
        
        return target_date.strftime('%Y-%m-%d')
    
    def login(self):
        """
        Performs a login operation to the website using credentials from environment variables.
        Sends Telegram notifications for login success or failure.
        
        Returns:
            bool: True if login is successful, False otherwise.
        """
        login_url = "https://jnrent2.jungnangimc.or.kr/bbs/login_check.php"
        
        login_data = {
            'rtn_url': 'https://jnrent2.jungnangimc.or.kr',
            'rtn_par': '',
            'mb_id': self.mb_id, 
            'mb_password': self.mb_password 
        }
        
        try:
            response = self.session.post(login_url, data=login_data)
            
            if response.status_code == 200:
                # Check for PHPSESSID cookie to confirm successful login
                session_id = self.session.cookies.get('PHPSESSID')
                if session_id:
                    print(f"로그인 성공! 쿠키값: {session_id}")
                    self.send_telegram_message("<b>로그인 성공!</b> ✅")
                    return True
                else:
                    print("로그인 실패: 쿠키를 받지 못했습니다.")
                    self.send_telegram_message("<b>로그인 실패:</b> 쿠키를 받지 못했습니다. ❌")
                    return False
            else:
                print(f"로그인 실패: HTTP 상태코드 {response.status_code}")
                self.send_telegram_message(f"<b>로그인 실패:</b> HTTP 상태코드 {response.status_code} ❌")
                return False
                
        except Exception as e:
            print(f"로그인 중 오류 발생: {str(e)}")
            self.send_telegram_message(f"<b>로그인 중 오류 발생:</b> {str(e)} ❌")
            return False
    
    def get_data_from_ajax(self, date, week_code, tr_index, td_index):
        """
        Fetches data from an AJAX request and extracts a specific value from a table.
        This value is typically part of the `cote_seq_arr[]` for reservation.
        
        Args:
            date (str): The date in 'YYYY-MM-DD' format.
            week_code (int): The week code for the AJAX request.
            tr_index (int): The 1-based index of the target table row (TR).
            td_index (int): The 1-based index of the target table data cell (TD).
            
        Returns:
            str: The extracted 'value' attribute from the checkbox input, or None if not found/error.
        """
        ajax_url = "https://jnrent2.jungnangimc.or.kr/page/rent/ajax.rent.od.proc.php"
        
        # Extract month from the date string
        month = int(date.split('-')[1])
        
        ajax_data = {
            'mode': 'rent_ymd_chk',
            'sct_key': '3',
            'mseason': str(month),
            'urent_d': date,
            'week_chk': str(week_code),
            'cote_cnt': '8'
        }
        
        print(f"  AJAX 요청 데이터: {ajax_data}")
        
        try:
            response = self.session.post(ajax_url, data=ajax_data)
            
            if response.status_code != 200:
                print(f"  AJAX 요청 실패: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with class 'stbl_l1a con_wid'
            table = soup.find('table', class_='stbl_l1a con_wid')
            
            # Fallback if the specific table class is not found
            if not table:
                print("  지정된 테이블을 찾을 수 없습니다. 다른 테이블 클래스 시도합니다.")
                table = soup.find('table', class_='stbl_l1a') # Try a broader class
                if not table:
                    print("  'stbl_l1a' 클래스 테이블도 찾을 수 없습니다.")
                    tables = soup.find_all('table') # Find all tables
                    if tables:
                        table = tables[0] # Use the first table found
                        print("  첫 번째 발견된 테이블을 사용합니다.")
                    else:
                        print("  HTML에서 어떤 테이블도 찾을 수 없습니다.")
                        return None
            
            # Find all TR elements within the table
            trs = table.find_all('tr')
            print(f"  발견된 TR 개수: {len(trs)}")
            
            if len(trs) < tr_index:
                print(f"  TR 인덱스 {tr_index}가 범위를 벗어났습니다. (총 TR 개수: {len(trs)})")
                return None
            
            # Find TDs within the specified TR
            target_tr = trs[tr_index - 1]  # Convert 1-based index to 0-based
            tds = target_tr.find_all('td')
            print(f"  TR {tr_index}의 TD 개수: {len(tds)}")
            
            if len(tds) < td_index:
                print(f"  TD 인덱스 {td_index}가 범위를 벗어났습니다. (총 TD 개수: {len(tds)})")
                return None
            
            # Extract the 'value' attribute from the checkbox input within the target TD
            target_td = tds[td_index - 1]  # Convert 1-based index to 0-based
            input_tag = target_td.find('input', type='checkbox')
            
            if input_tag:
                value = input_tag.get('value')
                if value:
                    print(f"  추출된 값: {value}")
                    return value
                else:
                    print("  input 태그에 value 속성이 없습니다.")
                    return None
            else:
                print("  checkbox input 태그를 찾을 수 없습니다.")
                return None
                
        except Exception as e:
            print(f"  AJAX 요청 중 오류 발생: {str(e)}")
            return None
    
    def generate_sequential_values(self, original_value, count):
        """
        Generates a sequence of values by incrementing the first number in the original value.
        This is used to get the specific `cote_seq_arr[]` values for different time slots.
        
        Args:
            original_value (str): The original value (e.g., "250100||4||20250803").
            count (int): The number of sequential values to generate.
            
        Returns:
            list: A list of integers representing the sequential first parts of the values.
        """
        if not original_value:
            print("  원본 값이 없습니다.")
            return []
            
        parts = original_value.split('||')
        if len(parts) < 3:
            print(f"  올바르지 않은 형식의 값: {original_value}")
            return []
            
        try:
            base_number = int(parts[0])
            
            result = []
            for i in range(count):
                result.append(base_number + i)
            
            print(f"  생성된 연속 값들: {result}")
            return result
            
        except ValueError:
            print(f"  숫자 변환 오류: {parts[0]}")
            return []
    
    def generate_monthly_reservations(self, year, month, sunday_values, wednesday_values, saturday_values):
        """
        Generates court reservation values for Sundays, Wednesdays, and Saturdays
        of the specified month and year. These values will be used as `cote_seq_arr[]`.
        
        Args:
            year (int): The year.
            month (int): The month (1-12).
            sunday_values (list): List of base values for Sunday reservations.
            wednesday_values (list): List of base values for Wednesday reservations.
            saturday_values (list): List of base values for Saturday reservations.
            
        Returns:
            list: A list of reservation strings (e.g., "250100||4||20250803").
        """
        print(f"\n=== generate_monthly_reservations 시작 ===")
        print(f"입력 데이터 - 일요일: {sunday_values}, 수요일: {wednesday_values}, 토요일: {saturday_values}")
        
        reservations = []
        
        # Calculate the first and last day of the month
        first_day_of_month = datetime(year, month, 1)
        last_day_of_month = datetime(year, month, calendar.monthrange(year, month)[1])

        current_date = first_day_of_month

        while current_date <= last_day_of_month:
            # Sunday (weekday() is 0=Monday, 6=Sunday)
            if current_date.weekday() == 6:  # Sunday
                print(f"  일요일 처리: {current_date.strftime('%Y-%m-%d')}")
                if len(sunday_values) >= 4:
                    # The '4' in '||4||' is a specific code within the reservation value structure.
                    # It's not a time slot, but part of the unique identifier for the booking.
                    reservations.append(f"{sunday_values[0]}||4||{current_date.strftime('%Y%m%d')}")  # First Sunday slot
                    reservations.append(f"{sunday_values[1]}||4||{current_date.strftime('%Y%m%d')}")  # Second Sunday slot
                    reservations.append(f"{sunday_values[2]}||4||{current_date.strftime('%Y%m%d')}")  # Third Sunday slot
                    reservations.append(f"{sunday_values[3]}||4||{current_date.strftime('%Y%m%d')}")  # Fourth Sunday slot
                else:
                    print(f"    일요일 값이 부족합니다: {len(sunday_values)} < 4")

            # Wednesday (weekday() is 0=Monday, 6=Sunday)
            elif current_date.weekday() == 2:  # Wednesday
                print(f"  수요일 처리: {current_date.strftime('%Y-%m-%d')}")
                if len(wednesday_values) >= 2:
                    # The '6' in '||6||' is a specific code within the reservation value structure.
                    reservations.append(f"{wednesday_values[0]}||6||{current_date.strftime('%Y%m%d')}")  # First Wednesday slot
                    reservations.append(f"{wednesday_values[1]}||6||{current_date.strftime('%Y%m%d')}")  # Second Wednesday slot
                else:
                    print(f"    수요일 값이 부족합니다: {len(wednesday_values)} < 2")
                
            # Saturday (weekday() is 0=Monday, 6=Sunday)
            elif current_date.weekday() == 5:  # Saturday
                print(f"  토요일 처리: {current_date.strftime('%Y-%m-%d')}")
                if len(saturday_values) >= 2:
                    # The '5' in '||5||' is a specific code within the reservation value structure.
                    reservations.append(f"{saturday_values[0]}||5||{current_date.strftime('%Y%m%d')}")  # First Saturday slot
                    reservations.append(f"{saturday_values[1]}||5||{current_date.strftime('%Y%m%d')}")  # Second Saturday slot
                else:
                    print(f"    토요일 값이 부족합니다: {len(saturday_values)} < 2")
                
            current_date += timedelta(days=1)
        
        print(f"  총 생성된 예약 개수: {len(reservations)}")
        return reservations
    
    def make_reservation(self, month, reservation_value):
        """
        Executes a web reservation using the provided reservation value.
        This function sends a POST request to the specified reservation URL.
        
        Args:
            month (int): The month for the reservation (used in payload 'mseason').
            reservation_value (str): The reservation string (e.g., "250100||4||20250803"),
                                     which goes into 'cote_seq_arr[]'.
            
        Returns:
            bool: True if the reservation appears successful, False otherwise.
        """
        reservation_url = "https://jnrent2.jungnangimc.or.kr//page/rent/_inc.cart.list.proc.php"
        
        # Set request headers including User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Reservation request payload as specified by the user
        reservation_payload = {
            "mode": "cart_list_rent",
            "sct_key": "3",
            "mseason": month, # Use the input month value
            "cote_seq_arr[]": reservation_value # Send a single reservation value per request
        }
        
        print(f"\n  === 예약 시도: {reservation_value} (월: {month}) ===")
        print(f"  예약 요청 데이터: {reservation_payload}")
        
        try:
            response = self.session.post(reservation_url, data=reservation_payload, headers=headers)
            
            # Check for success based on HTTP status code and specific text in the response
            if response.status_code == 200:
                # Check for "장바구니에 담았습니다." in the response text
                if '장바구니에 담았습니다.' in response.text:
                    # If "항목 제외하고" is also present, it's a partial success (someone else took it)
                    if '항목 제외하고' in response.text:
                        print(f"  **예약 부분 성공 (일부 항목 제외):** {reservation_value} ")
                        self.send_telegram_message(f"<b>이미 누가 선점:</b> {reservation_value} ⚠️")
                        return True # Considered a success for the function's return, but with a warning
                    else:
                        # Only "장바구니에 담았습니다." means full success
                        print(f"  **예약 성공 (장바구니에 담김):** {reservation_value}")
                        self.send_telegram_message(f"<b>예약 성공:</b> {reservation_value} ✅")
                        return True
                else:
                 
                    print(f"  **예약 실패 (응답 내용 확인 필요):** {response.text.strip()[:200]}...") # Print part of response for debugging
                    self.send_telegram_message(f"<b>예약 실패:</b> {reservation_value} ❌")
                    return False
            else:
                print(f"  예약 요청 실패: HTTP 상태코드 {response.status_code}")
                self.send_telegram_message(f"<b>예약 요청 실패:</b> {reservation_value} - HTTP {response.status_code} ❌")
                return False
               
        
        except Exception as e:
            print(f"  예약 실행 중 오류 발생: {str(e)}")
            self.send_telegram_message(f"<b>예약 실행 중 오류 발생:</b> {reservation_value} - {str(e)} ❌")
            return False

    def run_scraper(self, year, month):
        """
        Main function to run the scraping and reservation process.
        This function orchestrates login, data collection, and reservation attempts.
        
        Args:
            year (int): The year for data collection and reservation.
            month (int): The month for data collection and reservation.
            
        Returns:
            dict: A dictionary containing collected data, or None if login fails.
        """
        self.send_telegram_message(f"<b>예약 스크립트 시작:</b> {year}년 {month}월 🚀")
        
        # Perform login
        if not self.login():
            print("로그인 실패로 프로그램을 종료합니다.")
            self.send_telegram_message(f"<b>스크립트 종료:</b> 로그인 실패 ⛔")
            return None
        
        print(f"\n=== {year}년 {month}월 데이터 수집 시작 ===")
        
        # Calculate the first Sunday, Wednesday, and Saturday of the month
        first_sunday = self.get_first_weekday_of_month(year, month, 6)  # Sunday = 6
        first_wednesday = self.get_first_weekday_of_month(year, month, 2)  # Wednesday = 2
        first_saturday = self.get_first_weekday_of_month(year, month, 5)  # Saturday = 5
        
        print(f"\n{year}년 {month}월의 첫 번째 요일들:")
        print(f"첫 번째 일요일: {first_sunday}")
        print(f"첫 번째 수요일: {first_wednesday}")
        print(f"첫 번째 토요일: {first_saturday}")
        
        results = {}
        
        # 1. Collect Sunday data (week_chk = 0)
        print(f"\n=== 일요일 데이터 수집 ({first_sunday}) ===")
        # Assuming 2nd TR, 4th TD corresponds to the 6 AM court value
        sunday_value = self.get_data_from_ajax(first_sunday, 0, 2, 4)  
        
        sunday_values = []
        if sunday_value:
            sunday_values = self.generate_sequential_values(sunday_value, 4) # 4 sequential values for 6, 7, 8, 9 AM
            results['sunday'] = sunday_values
            print(f"일요일 생성된 값들: {sunday_values}")
        else:
            print("일요일 데이터 수집 실패")
            self.send_telegram_message(f"<b>데이터 수집 실패:</b> 일요일 데이터 ❌")
        
        # 2. Collect Wednesday data (week_chk = 3)
        print(f"\n=== 수요일 데이터 수집 ({first_wednesday}) =====")
        # Assuming 16th TR, 6th TD corresponds to the 8 PM court value
        wednesday_value = self.get_data_from_ajax(first_wednesday, 3, 16, 6)  
        
        wednesday_values = []
        if wednesday_value:
            wednesday_values = self.generate_sequential_values(wednesday_value, 2) # 2 sequential values for 8, 9 PM
            results['wednesday'] = wednesday_values
            print(f"수요일 생성된 값들: {wednesday_values}")
        else:
            print("수요일 데이터 수집 실패")
            self.send_telegram_message(f"<b>데이터 수집 실패:</b> 수요일 데이터 ❌")
        
        # 3. Collect Saturday data (week_chk = 6)
        print(f"\n=== 토요일 데이터 수집 ({first_saturday}) ===")
        # Assuming 14th TR, 5th TD corresponds to the 6 PM court value
        saturday_value = self.get_data_from_ajax(first_saturday, 6, 14, 5)  
        
        saturday_values = []
        if saturday_value:
            saturday_values = self.generate_sequential_values(saturday_value, 2) # 2 sequential values for 6, 7 PM
            results['saturday'] = saturday_values
            print(f"토요일 생성된 값들: {saturday_values}")
        else:
            print("토요일 데이터 수집 실패")
            self.send_telegram_message(f"<b>데이터 수집 실패:</b> 토요일 데이터 ❌")
        
        # Check if all necessary data was collected
        print(f"\n=== 데이터 수집 결과 확인 ===")
        print(f"일요일 값 개수: {len(sunday_values)}")
        print(f"수요일 값 개수: {len(wednesday_values)}")
        print(f"토요일 값 개수: {len(saturday_values)}")
        
        # Generate monthly reservation data if all base values are available
        if sunday_values and wednesday_values and saturday_values:
            print(f"\n=== {year}년 {month}월 전체 예약 데이터 생성 ===")
            monthly_reservations = self.generate_monthly_reservations(year, month, sunday_values, wednesday_values, saturday_values)
            
            print(f"생성된 예약 데이터 개수: {len(monthly_reservations)}")
            
            if monthly_reservations:
                results['monthly_reservations'] = monthly_reservations
                
                print("\n=== 실제 예약 실행 시작 ===")
                successful_reservations = 0
                for i, reservation_data in enumerate(monthly_reservations, 1):
                    print(f"[{i:2d}/{len(monthly_reservations)}] 예약 시도 중:")
                    if self.make_reservation(month, reservation_data): # Pass month and individual reservation data
                        successful_reservations += 1
                    time.sleep(1) # Add a 1-second delay between requests to reduce server load
                print("\n=== 실제 예약 실행 완료 ===")

                self.send_telegram_message(f"<b>예약 시도 완료:</b> 총 {len(monthly_reservations)}건 중 {successful_reservations}건 성공. 🎉")
                
            else:
                print("예약 데이터가 생성되지 않았습니다.")
                self.send_telegram_message(f"<b>스크립트 종료:</b> 예약 데이터 생성 실패 ⛔")
        else:
            print("필요한 데이터가 모두 수집되지 않았습니다:")
            print(f"  일요일 데이터: {'OK' if sunday_values else 'FAIL'}")
            print(f"  수요일 데이터: {'OK' if wednesday_values else 'FAIL'}")
            print(f"  토요일 데이터: {'OK' if saturday_values else 'FAIL'}")
            self.send_telegram_message(f"<b>스크립트 종료:</b> 필수 데이터 수집 실패 ⛔")
        
        # Final results output
        print(f"\n=== 최종 결과 ===")
        for day, values in results.items():
            if day != 'monthly_reservations':
                print(f"{day}: {values}")
        
        self.send_telegram_message(f"<b>스크립트 실행 완료:</b> {year}년 {month}월 예약 처리 완료. ✅")
        return results

# Example Usage
if __name__ == "__main__":
    # For automated execution (e.g., GitHub Actions), get the current month/year automatically.
    # This ensures the script always runs for the current month.
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    
    if not (current_date.weekday() == 0 and 1 <= current_date.day <= 7):
        print(f"오늘은 {current_date.strftime('%Y년 %m월 %d일')}입니다. 매월 첫째 주 월요일이 아니므로 스크립트를 종료합니다.")
        # Send a Telegram message for early exit if not the first Monday
        scraper_temp = WebScraper() # Create a temporary scraper instance to send message
        scraper_temp.send_telegram_message(f"<b>스크립트 종료:</b> {current_date.strftime('%Y년 %m월 %d일')} - 매월 첫째 주 월요일이 아님 😴")
        exit() # Exit the script if not the first Monday
        
    scraper = WebScraper()
    
    print(f"\n{year}년 {month}월 데이터 수집 및 예약 시도를 시작합니다...")
    results = scraper.run_scraper(year, month)
    
    if results and 'monthly_reservations' in results:
        print("\n=== 예약 실행 프로세스가 완료되었습니다. ===")
    else:
        print("예약 데이터 생성 및 실행에 실패했습니다.")


