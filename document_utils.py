from docx.shared import Pt
from num2words import num2words


def replace_text_in_document(doc, replacements):
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, str(value))


def replace_in_tables(tables, replacements):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in replacements.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, str(value))
                if cell.tables:
                    replace_in_tables(cell.tables, replacements)


def formatting_text(document):
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            run.font.name = 'Times New Roman'
            run.font.size = Pt(11)


def convert_to_currency_words(amount):
    hryvnia_part = int(amount)
    kopiyka_part = int(round((amount - hryvnia_part) * 100))
    hryvnia_words = num2words(hryvnia_part, lang='uk')
    kopiyka_words = num2words(kopiyka_part, lang='uk')
    return f"{hryvnia_words} гривень {kopiyka_words} копійок"


def format_date(date):
    months_ukr = {
        1: 'січня', 2: 'лютого', 3: 'березня', 4: 'квітня', 5: 'травня', 6: 'червня',
        7: 'липня', 8: 'серпня', 9: 'вересня', 10: 'жовтня', 11: 'листопада', 12: 'грудня'
    }
    day = date.strftime("%d")
    month = months_ukr[date.month]
    year = date.strftime("%Y")
    return f"{day} {month} {year} року", month, year, day


def amount_to_time(protocol_amount):
    work_hours = protocol_amount / 1000
    hours = int(work_hours)
    minutes = int((work_hours - hours) * 60)
    return f"{hours} годин {minutes} хвилин"


def create_table(doc, data, headers):
    table = doc.add_table(rows=1, cols=len(headers))

    hdr_cells = table.rows[0].cells
    for idx, header in enumerate(headers):
        hdr_cells[idx].text = header

    for row in data:
        row_cells = table.add_row().cells
        for idx, val in enumerate(row):
            row_cells[idx].text = str(val)

    return table


def replace_table_in_document(doc, marker, table):
    for paragraph in doc.paragraphs:
        if marker in paragraph.text:
            paragraph.clear()
            paragraph._element.addnext(table._element)
            break
    return doc
