from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
import csv
import os
from datetime import date, datetime, timedelta

app = Flask(__name__)
app.secret_key = 'my_secret_key_123'

# تنظیمات فایل‌ها
CSV_FILE = 'data.csv'
LOANS_FILE = 'loans.csv'
RESERVES_FILE = 'reserves.csv'
USERS_FILE = 'librarians.csv'
REPORTS_FILE = 'daily_reports.csv'
DAILY_FINE = 1000
LOAN_DAYS = 7

# ------------------------------------------------------------
# توابع کمکی
# ------------------------------------------------------------
def ensure_files():
    """ایجاد فایل‌های CSV در صورت عدم وجود"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'category', 'available', 'total'])
    if not os.path.exists(LOANS_FILE):
        with open(LOANS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'item_id', 'user_name', 'loan_date', 'due_date', 'return_date', 'renew_count', 'late_fine', 'damage_fine', 'damage_desc'])
    if not os.path.exists(RESERVES_FILE):
        with open(RESERVES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'item_id', 'user_name', 'reserve_date', 'status', 'notified'])
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'full_name', 'username', 'password', 'join_date'])
    if not os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'user_id', 'username', 'login_time', 'logout_time', 'daily_work', 'date'])

ensure_files()

def get_next_id(file_path):
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            return int(rows[-1][0]) + 1 if len(rows) > 1 else 1
    except:
        return 1

def clean_date(date_str):
    if not date_str:
        return ''
    return date_str.split('T')[0]

def get_reserve_queue(item_id):
    """دریافت صف انتظار رزرو برای یک کتاب خاص (مرتب‌سازی بر اساس تاریخ)"""
    queue = []
    with open(RESERVES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['item_id'] == str(item_id) and row['status'] == 'active':
                queue.append({'user_name': row['user_name'], 'reserve_date': row['reserve_date']})
    queue.sort(key=lambda x: x['reserve_date'])
    return queue

# ------------------------------------------------------------
# مسیرهای لاگین، ثبت‌نام و احراز هویت
# ------------------------------------------------------------
@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not full_name or not username or not password:
            return "<script>alert('همه فیلدها را پر کنید'); location.href='/register';</script>"
        
        # بررسی تکراری نبودن نام کاربری
        with open(USERS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['username'] == username:
                    return "<script>alert('این نام کاربری قبلاً ثبت شده است'); location.href='/register';</script>"
        
        new_id = get_next_id(USERS_FILE)
        join_date = date.today().isoformat()
        with open(USERS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([new_id, full_name, username, password, join_date])
        
        return "<script>alert('ثبت‌نام با موفقیت انجام شد. حالا وارد شوید.'); location.href='/login';</script>"
    
    return send_from_directory('.', 'register.html')

@app.route('/do_login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    
    with open(USERS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == username and row['password'] == password:
                session['logged_in'] = True
                session['username'] = username
                session['full_name'] = row['full_name']
                session['user_id'] = row['id']
                
                # ثبت ساعت ورود
                login_time = datetime.now().strftime('%H:%M:%S')
                today = date.today().isoformat()
                report_id = get_next_id(REPORTS_FILE)
                with open(REPORTS_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([report_id, row['id'], username, login_time, '', '', today])
                
                return redirect('/')
    
    return "<script>alert('نام کاربری یا رمز عبور اشتباه است'); location.href='/login';</script>"

@app.route('/logout', methods=['POST'])
def logout():
    if session.get('logged_in'):
        username = session.get('username')
        daily_work = request.form.get('daily_work', '').strip()
        logout_time = datetime.now().strftime('%H:%M:%S')
        today = date.today().isoformat()
        
        # بروزرسانی آخرین رکورد این کاربر امروز
        reports = []
        with open(REPORTS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            reports = list(reader)
        
        for i, row in enumerate(reports):
            if row[2] == username and row[6] == today and row[4] == '':
                reports[i][4] = logout_time
                reports[i][5] = daily_work
                break
        
        with open(REPORTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(reports)
    
    session.clear()
    return redirect('/login')

# ------------------------------------------------------------
# مسیرهای اصلی پروژه
# ------------------------------------------------------------
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    return send_from_directory('.', 'index.html')

@app.route('/check')
def check_status():
    return send_from_directory('.', 'check_status.html')

@app.route('/items')
def get_items():
    items = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                'id': row['id'],
                'name': row['name'],
                'category': row.get('category', 'متفرقه'),
                'available': int(row['available']),
                'total': int(row['total']),
                'queue_count': len(get_reserve_queue(row['id']))
            })
    return jsonify(items)

@app.route('/add', methods=['POST'])
def add_item():
    data = request.get_json()
    name = data['name']
    category = data.get('category', 'متفرقه')
    total = int(data['available'])
    new_id = get_next_id(CSV_FILE)
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([new_id, name, category, total, total])
    return jsonify({'status': 'ok'})

@app.route('/borrow', methods=['POST'])
def borrow():
    data = request.get_json()
    item_id = int(data['item_id'])
    user_name = data['user_name'].strip()
    
    if not user_name:
        return jsonify({'status': 'error', 'message': 'نام امانت‌گیرنده الزامی است'})
    
    rows = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    item_idx = -1
    for i, row in enumerate(rows):
        if int(row[0]) == item_id:
            item_idx = i
            break
    
    if item_idx == -1:
        return jsonify({'status': 'error', 'message': 'کتاب یافت نشد'})
    
    available = int(rows[item_idx][3])
    if available <= 0:
        return jsonify({'status': 'error', 'message': 'موجودی کافی نیست'})
    
    rows[item_idx][3] = str(available - 1)
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    
    loan_id = get_next_id(LOANS_FILE)
    loan_date = date.today().isoformat()
    due_date = (date.today() + timedelta(days=LOAN_DAYS)).isoformat()
    with open(LOANS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([loan_id, item_id, user_name, loan_date, due_date, '', '0', '0', '0', ''])
    
    # حذف از صف رزرو (رفع باگ)
    reserves = []
    with open(RESERVES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header_res = next(reader)
        reserves = list(reader)
    
    updated = False
    for i, res in enumerate(reserves):
        if len(res) > 4 and int(res[1]) == item_id and res[2].strip().lower() == user_name.strip().lower() and res[4] == 'active':
            reserves[i][4] = 'completed'
            updated = True
            break
    
    if updated:
        with open(RESERVES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header_res)
            writer.writerows(reserves)
    
    return jsonify({'status': 'ok', 'due_date': due_date})

@app.route('/return', methods=['POST'])
def return_item():
    data = request.get_json()
    loan_id = int(data['loan_id'])
    damage_fine = int(data.get('damage_fine', 0))
    damage_desc = data.get('damage_desc', '').strip()
    
    loans = []
    with open(LOANS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        loans = list(reader)
    
    loan_idx = -1
    for i, loan in enumerate(loans):
        if len(loan) > 5 and int(loan[0]) == loan_id and loan[5] == '':
            loan_idx = i
            break
    
    if loan_idx == -1:
        return jsonify({'status': 'error', 'message': 'امانت فعال یافت نشد'})
    
    loan = loans[loan_idx]
    item_id = int(loan[1])
    due_date = clean_date(loan[4])
    return_date = date.today().isoformat()
    
    late_fine = 0
    if return_date > due_date:
        days_late = (datetime.strptime(return_date, '%Y-%m-%d') - datetime.strptime(due_date, '%Y-%m-%d')).days
        late_fine = days_late * DAILY_FINE
    
    loans[loan_idx][5] = return_date
    loans[loan_idx][7] = str(late_fine)
    loans[loan_idx][8] = str(damage_fine)
    loans[loan_idx][9] = damage_desc if damage_desc else '---'
    
    with open(LOANS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(loans)
    
    items = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header2 = next(reader)
        items = list(reader)
    
    for i, item in enumerate(items):
        if int(item[0]) == item_id:
            items[i][3] = str(int(item[3]) + 1)
            break
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header2)
        writer.writerows(items)
    
    queue = get_reserve_queue(item_id)
    next_user = queue[0]['user_name'] if queue else None
    item_name = ""
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['id']) == item_id:
                item_name = row['name']
                break
    
    message = f"برگشت ثبت شد. جریمه دیرکرد: {late_fine} - جریمه آسیب: {damage_fine}"
    if next_user:
        message += f" | اطلاع رسانی: {next_user} عزیز، کتاب '{item_name}' برگشت خورد."
        
        reserves = []
        with open(RESERVES_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header_res = next(reader)
            reserves = list(reader)
        
        for i, res in enumerate(reserves):
            if len(res) > 1 and int(res[1]) == item_id and res[2] == next_user and res[4] == 'active':
                if len(res) > 5:
                    reserves[i][5] = 'yes'
                else:
                    while len(reserves[i]) < 6:
                        reserves[i].append('')
                    reserves[i][5] = 'yes'
                break
        
        with open(RESERVES_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header_res)
            writer.writerows(reserves)
    
    return jsonify({'status': 'ok', 'fine': late_fine + damage_fine, 'message': message, 'next_user': next_user})

@app.route('/renew', methods=['POST'])
def renew_loan():
    data = request.get_json()
    loan_id = int(data['loan_id'])
    user_name = data.get('user_name', '')
    
    loans = []
    with open(LOANS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        loans = list(reader)
    
    for i, loan in enumerate(loans):
        if len(loan) > 5 and int(loan[0]) == loan_id and loan[5] == '':
            item_id = int(loan[1])
            
            queue = get_reserve_queue(item_id)
            if queue and queue[0]['user_name'] != user_name:
                return jsonify({'status': 'error', 'message': f'امکان تمدید نیست. این کتاب توسط {queue[0]["user_name"]} رزرو شده است.'})
            
            renew_count = int(loan[6]) if len(loan) > 6 else 0
            if renew_count >= 2:
                return jsonify({'status': 'error', 'message': 'حداکثر ۲ بار می‌توان تمدید کرد.'})
            
            old_due = datetime.strptime(clean_date(loan[4]), '%Y-%m-%d')
            new_due = (old_due + timedelta(days=LOAN_DAYS)).isoformat()
            loans[i][4] = new_due
            loans[i][6] = str(renew_count + 1)
            
            with open(LOANS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(loans)
            
            return jsonify({'status': 'ok', 'new_due_date': new_due, 'message': f'تمدید شد. سررسید جدید: {new_due}'})
    
    return jsonify({'status': 'error', 'message': 'امانت یافت نشد'})

@app.route('/reserve', methods=['POST'])
def reserve_item():
    data = request.get_json()
    item_id = int(data['item_id'])
    user_name = data['user_name'].strip()
    
    if not user_name:
        return jsonify({'status': 'error', 'message': 'نام عضو الزامی است'})
    
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['id']) == item_id:
                if int(row['available']) > 0:
                    return jsonify({'status': 'error', 'message': 'کتاب موجود است، می‌توانید امانت بگیرید.'})
                break
    
    with open(RESERVES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['item_id'] == str(item_id) and row['user_name'] == user_name and row['status'] == 'active':
                return jsonify({'status': 'error', 'message': 'شما قبلاً این کتاب را رزرو کرده‌اید.'})
    
    reserve_id = get_next_id(RESERVES_FILE)
    today = date.today().isoformat()
    with open(RESERVES_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([reserve_id, item_id, user_name, today, 'active', 'no'])
    
    queue = get_reserve_queue(item_id)
    position = len(queue)
    
    return jsonify({'status': 'ok', 'message': f'رزرو برای "{user_name}" ثبت شد. جایگاه شما در صف: {position}', 'position': position})

@app.route('/active_loans')
def active_loans():
    loans_list = []
    with open(LOANS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['return_date'] == '':
                item_name = ''
                with open(CSV_FILE, newline='', encoding='utf-8') as f2:
                    reader2 = csv.DictReader(f2)
                    for it in reader2:
                        if it['id'] == row['item_id']:
                            item_name = it['name']
                            break
                
                today = date.today().isoformat()
                due_date_clean = clean_date(row['due_date'])
                days_left = 0
                if today <= due_date_clean:
                    days_left = (datetime.strptime(due_date_clean, '%Y-%m-%d') - datetime.strptime(today, '%Y-%m-%d')).days
                else:
                    days_left = - (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(due_date_clean, '%Y-%m-%d')).days
                
                loans_list.append({
                    'loan_id': row['id'],
                    'item_name': item_name,
                    'user_name': row['user_name'],
                    'loan_date': clean_date(row['loan_date']),
                    'due_date': due_date_clean,
                    'renew_count': int(row['renew_count']) if row['renew_count'] else 0,
                    'days_left': days_left
                })
    return jsonify(loans_list)

@app.route('/history')
def history():
    history_list = []
    with open(LOANS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_name = ''
            with open(CSV_FILE, newline='', encoding='utf-8') as f2:
                reader2 = csv.DictReader(f2)
                for it in reader2:
                    if it['id'] == row['item_id']:
                        item_name = it['name']
                        break
            
            due_date_clean = clean_date(row['due_date'])
            return_date_clean = clean_date(row['return_date']) if row['return_date'] else ''
            
            days_late = 0
            if return_date_clean and return_date_clean > due_date_clean:
                days_late = (datetime.strptime(return_date_clean, '%Y-%m-%d') - datetime.strptime(due_date_clean, '%Y-%m-%d')).days
            
            total_fine = int(row['late_fine']) + int(row['damage_fine'])
            history_list.append({
                'item_name': item_name,
                'user_name': row['user_name'],
                'loan_date': clean_date(row['loan_date']),
                'due_date': due_date_clean,
                'return_date': return_date_clean if row['return_date'] else '---',
                'late_fine': row['late_fine'],
                'damage_fine': row['damage_fine'],
                'damage_desc': row['damage_desc'] if row['damage_desc'] else '---',
                'days_late': days_late,
                'total_fine': total_fine
            })
    return jsonify(history_list)

@app.route('/reservations')
def get_reservations():
    reserves = []
    with open(RESERVES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'active':
                item_name = ''
                with open(CSV_FILE, newline='', encoding='utf-8') as f2:
                    reader2 = csv.DictReader(f2)
                    for it in reader2:
                        if it['id'] == row['item_id']:
                            item_name = it['name']
                            break
                
                queue = get_reserve_queue(int(row['item_id']))
                position = 1
                for i, q in enumerate(queue):
                    if q['user_name'] == row['user_name']:
                        position = i + 1
                        break
                
                reserves.append({
                    'item_name': item_name,
                    'user_name': row['user_name'],
                    'reserve_date': row['reserve_date'],
                    'position': position,
                    'notified': row.get('notified', 'no')
                })
    return jsonify(reserves)

# ------------------------------------------------------------
# مسیرهای جدید برای مدیریت کتابداران و گزارش‌ها
# ------------------------------------------------------------
@app.route('/get_librarians')
def get_librarians():
    librarians = []
    with open(USERS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            librarians.append({
                'id': row['id'],
                'full_name': row['full_name'],
                'username': row['username'],
                'join_date': row['join_date']
            })
    return jsonify(librarians)

@app.route('/get_today_reports')
def get_today_reports():
    today = date.today().isoformat()
    reports = []
    with open(REPORTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date'] == today:
                reports.append({
                    'username': row['username'],
                    'login_time': row['login_time'],
                    'logout_time': row['logout_time'],
                    'daily_work': row['daily_work']
                })
    return jsonify(reports)

# ------------------------------------------------------------
# مسیر حذف کتاب
# ------------------------------------------------------------
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    # بررسی امانت فعال
    with open(LOANS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['item_id']) == item_id and row['return_date'] == '':
                return "<script>alert('این کتاب در امانت فعال دارد و قابل حذف نیست'); location.href='/';</script>"
    
    # حذف از فایل data.csv
    rows = []
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    
    new_rows = [row for row in rows if int(row[0]) != item_id]
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(new_rows)
    
    return "<script>alert('کتاب با موفقیت حذف شد'); location.href='/';</script>"

# ------------------------------------------------------------
# راه‌اندازی سرور
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)