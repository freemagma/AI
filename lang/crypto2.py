import re
import sys
from collections import namedtuple

Attempt = namedtuple("Attempt", "success decode_updates affected")
Solution = namedtuple("Solution", "decode message rank")

true_words = re.compile(r'^(?=\w*[aeiouyw]\w*$)(?=.{2,}|a$|i$).*', re.M|re.I)
improper_chars = re.compile(r"[^A-Z]")

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

class Litecoin:
    def __init__(self, code, dict_name='wordss', freq_name='freq', callback=print):
        self.callback = callback
        self.code = code.upper()
        self.dictl = create_dictl(dict_name)
        self.freqrank = create_freqrank(freq_name)
        self.words = [improper_chars.sub('', w) for w in self.code.split()]
        self.unsolved = set(ALPHABET)
        self.decode = {}
        self.posset = {l : None for l in ALPHABET}
        for l in ALPHABET:
            self.update_possibilities(l)
        self.solution = None
    def solve(self):
        if not self.unsolved:
            return True
        let = min(self.unsolved, key=self.reducability)
        for poss in sorted(self.posset[word], key=self.frequency, reverse=True):
            #print('try:  {} => {}'.format(self.message(word), poss.lower()))
            a = self.try_possibility(word, poss)
            if a.success:
                solved = self.solve()
                if solved: return True
            self.untry_possibility(word, poss, a)
            #print('fail: {} => {}'.format(self.message(word), poss.lower()))
        return False
    def try_possibility(self, word, poss):
        self.unsolved.remove(word)
        decode_updates = {}
        for wc, pc in zip(word, poss):
            if wc not in self.decode:
                decode_updates[wc] = pc
        if not decode_updates:
            return Attempt(True, decode_updates, set())
        self.decode.update(decode_updates)
        affected = set()
        success = True
        for w in sorted(self.unsolved, key=lambda w: self.reducability(w, decode_updates)):
            affected.add(w)
            self.posset[w].save()
            self.update_possibilities(w)
            if len(self.posset[w]) == 0:
                success = False
                #print("due: {}".format(w))
                break
        return Attempt(success, decode_updates, affected)
    def untry_possibility(self, word, poss, a):
        self.unsolved.add(word)
        for k in a.decode_updates:
            self.decode.pop(k)
        for w in a.affected:
            self.posset[w].restore()
            if len(self.posset[w]) > 1:
                self.unsolved.add(w)
    def solution_rank(self):
        tot = 0
        for w in self.words:
            decoded_w = str([self.decode[c] for c in w])
            tot += self.frequency(decoded_w)
        return tot
    def reducability(self, word, decode_updates={}):
        return len(self.posset[word])
    def frequency(self, word):
        rank = self.freqrank.get(word)
        return rank if rank is not None else len(self.freqrank)
    def update_possibilities(self, word):
        pattern = '^'
        backref = {}
        next_backref = 1
        for c in word:
            if c in self.decode:
                pattern += self.decode[c]
            elif c in backref:
                pattern += backref[c]
            else:
                union = [*backref.values(), *self.decode.values()]
                if len(union) > 0:
                    pattern += '(?!{})'.format('|'.join(union))
                pattern += '(.)'
                backref[c] = '\\' + str(next_backref)
                next_backref += 1
        regex = re.compile(pattern + '$')
        if self.posset[word] is not None:
            to_hide = set()
            for p in self.posset[word]:
                if not regex.match(p):
                    to_hide.add(p)
            for p in to_hide:
                self.posset[word].hide(p)
        else:
            self.posset[word] = Domain([])
            for p in self.dictl[len(word)-1]:
                if regex.match(p):
                    self.posset[word].add(p)
    def message(self, code=None, show_unknowns=True, use_solution=False):
        table = self.decode
        if use_solution and self.solution is not None:
            table = self.solution
        if code is None:
            code = self.code
        message = ''
        for c in code:
            if c not in ALPHABET:
                message += c
            elif c in table:
                message += table[c].lower()
            elif show_unknowns:
                 message += c
            else:
                message += '?'
        return message

class Domain(set):
    def __init__(self, it):
        set.__init__(self, it)
        self.hidden = []
        self.pastlen = []
    def hide(self, val):
        if val not in self: return
        self.remove(val)
        if self.pastlen: self.hidden.append(val)
    def save(self):
        self.pastlen.append(len(self))
    def restore(self):
        if not self.pastlen: return False
        dif = self.pastlen.pop() - len(self)
        if dif == 0: return
        self.update(self.hidden[-dif:])
        del self.hidden[-dif:]
        return True

def create_freqrank(freq_name):
    with open('docs/{}.txt'.format(freq_name)) as f:
        return {w.strip().upper() : int(c) for w, c in map(lambda l: tuple(l.split()), list(f))}

def create_dictl(dict_name):
    dictl = []
    with open('docs/{}.txt'.format(dict_name)) as f:
        allwords = f.read()
        for w in true_words.findall(allwords):
            if len(w) > len(dictl):
                dictl.extend([set() for _ in range(len(w)-len(dictl))])
            dictl[len(w)-1].add(w.upper())
    return dictl

def main():
    code = sys.argv[1]
    decrypt(code)

def decrypt(code):
    def display(sol):
        print(sol.message)
        return True
    e = Litecoin(code, callback=display)
    e.solve()

if __name__ == "__main__": main()
