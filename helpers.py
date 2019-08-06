import datetime
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
import constants as c

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name(c.CREDENTIALS_FILE, scope)

gc = gspread.authorize(credentials)


def param_to_int(argument_index):
    """
    converts argument with specified index to int (if possible)
    :param argument_index: int
    """

    def real_decorator(func):
        def wrapper(*args, **kwargs):
            if len(args) > argument_index:
                args = list(args)

                try:
                    args[argument_index] = int(args[argument_index])
                except:
                    pass

            return func(*args, **kwargs)

        return wrapper

    return real_decorator


def get_document(url):
    try:
        sh = gc.open_by_url(url)
        return sh
    except:
        return None


def get_worksheets(url):
    try:
        sh = get_document(url)
        return sh.worksheets()
    except:
        return None


@param_to_int(1)
def get_worksheet_by_id(url, worksheet_id):
    worksheets = get_worksheets(url)

    if worksheets is None:
        return

    for ws in worksheets:
        if ws.id == worksheet_id:
            return ws


def validate_worksheet(url, worksheet_id):
    return bool(get_worksheet_by_id(url, worksheet_id))


def is_worksheet_empty(url, worksheet_id):
    worksheet = get_worksheet_by_id(url, worksheet_id)

    return worksheet and (not bool(worksheet.get_all_values()))


def clear_worksheet(url, worksheet_id):
    worksheet = get_worksheet_by_id(url, worksheet_id)

    worksheet.clear()


def create_worksheet(url, worksheet_name):
    sh = get_document(url)

    ws = sh.add_worksheet(worksheet_name, rows="50000", cols="20")
    return ws


def parse_new_spendings(text):
    date_available = re.findall(r"(?:@[\s]*)(?P<date>[\d.]*)(?:[\s]*)(?P<time>[\d.:]*)?(?:[\s]*)$", text)

    if date_available:
        date_available = date_available[0]

        if date_available[0].count('.') == 1:
            date_available[0] += '.{year}'.format(year=datetime.datetime.now().year)

        date_spent = datetime.datetime.strptime(
            '{date} {time}'.format(date=date_available[0], time=date_available[1].replace('.', ':')), '%d.%m.%Y %H:%M'
        )
        text = text[:text.rindex('@')]
    else:
        date_spent = datetime.datetime.now()

    split_result = [x[-1].strip() for x in re.findall(r"((?:[\s]*)?(?:[,;+]*)(?:[\s]*)?([^,;+]+))+?", text)]

    spending_regex = r"([\d.]+)(?:[\s]+)([^,;+]+?)(x[\d]+[^,;+\s]*)?$"
    spendings = []

    for pre_data in map(lambda raw_spending: re.match(spending_regex, raw_spending).groups(), split_result):
        data = {
            'price': float(pre_data[0]),
            'name': pre_data[1].strip(),
            'quantity': pre_data[2][1:] if len(pre_data) > 2 else ''
        }

        spendings.append(data)

    return date_available, spendings
