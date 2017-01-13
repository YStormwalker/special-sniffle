'''
Ver. 1.3
 Implemented unittests.
 Text processing broken into smaller functions.
 Routine function now works with only one file permanently.
'''


import re
from nltk.stem.snowball import RussianStemmer
from nltk.corpus import stopwords
from alphabet_detector import AlphabetDetector
from collections import Counter
from multiprocessing import Pool
import sqlite3
import unittest


def getText(path):
    '''
    Function that returns string with text from asked file.
    '''
    with open(path, encoding='utf-8') as file:
        text = file.read()

    return text


def preprod(text):
    '''
    Drop all non-letter characters from text, split string into words,
    return list of lowercase words.
    '''

    text = re.sub('[^A-Za-zА-Яа-я]', ' ', text).split()
    text = [word.lower() for word in text if len(word) > 2]

    return text


def letterSwap(word):
    '''
    Turns latin-like letters in word into cyrillic ones and reverse if fails.
    '''

    ad = AlphabetDetector()
    # latin keys cyr values
    latin_like_cyr = {'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р',
                      'y': 'у', 'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е',
                      'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р',
                      'T': 'Т', 'X': 'Х'}

    cyr_like_latin = {v: k for k, v in latin_like_cyr.items()}

    for char in latin_like_cyr.keys():
        word = word.replace(char, latin_like_cyr[char])

    if ad.only_alphabet_chars(word, 'CYRILLIC'):
        return word
    else:
        for char in cyr_like_latin:
            word = word.replace(char, cyr_like_latin[char])
        return word


def cleanText(text):
    '''
     Function checks and repairs words with hidden latin characters in and vv.
     Function assuming that there are only latin and cyrillic characters
     in text.
    '''

    ad = AlphabetDetector()
    st = RussianStemmer()
    is_broken = False

    clean_text = []

    for word in text:
        if ad.only_alphabet_chars(word, 'CYRILLIC'):
            clean_text.append(word)
        elif ad.only_alphabet_chars(word, 'LATIN'):
            clean_text.append(word)
        else:
            is_broken = True
            clean_text.append(letterSwap(word))

    clean_text = [st.stem(word) for word in clean_text]
    return clean_text, is_broken


def nauseaRate(text):
    commons_count = 0
    commons = Counter(text)

    if not text:
        return 0

    for x in range(5):
        commons_count += commons.most_common(5)[x][1]
    nausea = commons_count / len(text)

    return nausea


def sqlSubmit(data):
    '''
     Submit results to table
    '''
    conn = sqlite3.connect('nausea.db')
    with conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS text_info')
        # print('Table dropped')
        c.execute(
            'CREATE TABLE text_info (filename TEXT, nausea REAL, cheat INT)')
        # print('Table created')
        c.executemany('INSERT INTO text_info VALUES (?,?,?)', data)
    conn.commit()


class ut_case(unittest.TestCase):

    def test_letterSwap(self):
        '''
         Some letters in first elements of cases are swapped with latin equals.
         letterSwap function should find them and swap with cyrillic ones
        '''
        cases = [('привeт', 'привет'), ('кoшка', 'кошка'), ('Нellо', 'Hello'),
                 ('саt', 'cat')]
        for case in cases:
            self.assertEqual(letterSwap(case[0]), case[1])

    def test_text_preproduction(self):
        '''
        This test checks how preprod function splits text into words.
        '''
        lorem_ipsum_ru = 'Далеко-далеко за словесными горами в стране \
                         гласных и согласных живут рыбные тексты. Вдали \
                         от всех живут они в буквенных домах на берегу \
                         Семантика большого языкового океана. Маленький \
                         ручеек Даль журчит по всей стране и обеспечивает ее \
                         всеми необходимыми правилами.'

        pre_stem = ['далеко', 'далеко', 'словесными', 'горами', 'стране',
                    'гласных', 'согласных', 'живут', 'рыбные', 'тексты',
                    'вдали', 'всех', 'живут', 'они', 'буквенных', 'домах',
                    'берегу', 'семантика', 'большого', 'языкового', 'океана',
                    'маленький', 'ручеек', 'даль', 'журчит', 'всей', 'стране',
                    'обеспечивает', 'всеми', 'необходимыми', 'правилами']

        self.assertEqual(preprod(lorem_ipsum_ru), pre_stem)

    def test_text_repair(self):
        '''
        This test compares stemming of fine text and 'fraud' text.
        '''
        upright_pre_stem = ['далеко', 'далеко', 'словесными', 'горами',
                            'стране', 'гласных', 'согласных', 'живут',
                            'рыбные', 'тексты', 'вдали', 'всех', 'живут',
                            'они', 'буквенных', 'домах', 'берегу', 'семантика',
                            'большого', 'языкового', 'океана', 'маленький',
                            'ручеек', 'даль', 'журчит', 'всей', 'стране',
                            'обеспечивает', 'всеми', 'необходимыми',
                            'правилами']

        # same text but some letters changed into latin ones at random
        broken_pre_stem = ['дaлеко', 'далеко', 'словeсными', 'горaми',
                           'стране', 'гласных', 'соглaсных', 'живут', 'рыбные',
                           'тексты', 'вдали', 'всех', 'живyт', 'они',
                           'бyквенных', 'домах', 'берегу', 'семантика',
                           'большого', 'языкового', 'oкeана', 'маленький',
                           'ручеек', 'даль', 'журчит', 'всей', 'стране',
                           'обеспечивает', 'всеми', 'необходимыми',
                           'правилами']

        self.assertEqual(cleanText(upright_pre_stem)[0],
                         cleanText(broken_pre_stem)[0])


def routine(path):
    filename = re.findall(r'\w+\.txt$', path)[0]
    text = getText(path)
    raw_text = preprod(text)
    clean_text, is_broken = cleanText(raw_text)
    nausea = nauseaRate(clean_text)

    return filename, nausea, is_broken


if __name__ == '__main__':
    indexes = [str(index)[-4:] for index in range(10001, 10106)]
    paths = ['text_files/' + index + '.txt' for index in indexes]

    p = Pool()

    results = p.map(routine, paths)

    p.close()
    p.join()
    sqlSubmit(results)
