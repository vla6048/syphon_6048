from num2words import num2words

sum = '666.54'
summa = float(sum)
print(summa)

def convert_to_currency_words(amount):
    hryvnia_part = int(amount)
    kopiyka_part = int(round((amount - hryvnia_part) * 100))
    hryvnia_words = num2words(hryvnia_part, lang='uk')
    kopiyka_words = num2words(kopiyka_part, lang='uk')
    return f"{hryvnia_words} гривень {kopiyka_words} копійок"


print(convert_to_currency_words(666.54))