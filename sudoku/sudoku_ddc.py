import sys, cProfile, time
from functools import reduce

class Deducer:
    def __init__(self, p, t):
        self.t = t
        self.board = ['.' for _ in range(self.t.cells)]
        self.vals = values(p, t.side)
        self.opts = {(0, i) : self.vals.copy() for i in range(t.cells)}
        self.opts.update({(1, val, unit) : t.groups[unit].copy() for val in self.vals for unit in range(t.side*3)})
        self.empty = set(self.opts.keys())
        for ix, v in filter(lambda t: t[1] != '.', enumerate(p)): self.assign((0, ix), v)
    def deduce(self):
        prev_sum_opts = sum(map(lambda x: len(x), self.opts.values()))
        loops = 0
        while True:
            loops += 1
            self.altpair_deduce()
            self.shareset_deduce()
            self.preempt_deduce()
            new_sum_opts = sum(map(lambda x: len(x), self.opts.values()))
            if new_sum_opts == prev_sum_opts: break
            prev_sum_opts = new_sum_opts
        print("deduction loops:", loops)
    def preemptive_sets(self, keys):
        partial = {frozenset(): 0}
        total = []
        for o in map(lambda k: frozenset(self.opts[k]), keys):
            new_partial = {}
            for s, count in partial.items():
                new = o | s
                if new in partial: partial[new] = max(partial[new], count+1)
                else: new_partial[new] = count+1
                if len(new) == count+1: total.append(new)
            partial.update(new_partial)
        return total
    def shareset_deduce(self):
        if not self.empty: return
        toremove = [set() for ix in range(self.t.cells)]
        for g in range(self.t.side*3):
            for val in self.vals:
                if (1, val, g) not in self.empty: continue
                shared = reduce(lambda a, b: a & b, [self.t.cellgroups[ix] for ix in self.opts[(1, val, g)]]) - {g}
                if len(shared) == 0: continue
                shared = next(iter(shared))
                for ix in (self.t.groups[shared] - self.opts[(1, val, g)]):
                    toremove[ix].add(val)
        for ix in range(self.t.cells):
            for val in toremove[ix]:
                self.removeassign(ix, val)
    def altpair_deduce(self):
        if not self.empty: return
        for val in self.vals: self.altpair_deduce_val(val)
    def altpair_deduce_val(self, val):
        alts = {}
        for g in range(self.t.side*3):
            if len(self.opts[(1, val, g)]) == 2:
                pair = tuple(self.opts[(1, val, g)])
                for ix, c in enumerate(pair):
                    if c in alts: alts[c].add(pair[1-ix])
                    else: alts[c] = {pair[1-ix]}
        toremovefrom = set()
        uncolored = set(alts.keys())
        fail = None
        def color(ix, c, c_opp):
            if ix in c_opp: fail = c_opp
            elif ix not in c:
                c.add(ix)
                for a in alts[ix]: color(a, c_opp, c)
        while uncolored:
            tocolor = next(iter(uncolored))
            c1, c2 = set(), set()
            color(tocolor, c1, c2)
            uncolored -= (c1 | c2)
            if fail:
                toremovefrom |= fail
                continue
            c1peers = reduce(lambda a, b: a | b, [self.t.peers[i] for i in c1])
            c2peers = reduce(lambda a, b: a | b, [self.t.peers[i] for i in c2])
            toremovefrom |= c1peers & c2peers
        for ix in toremovefrom: self.removeassign(ix, val)
    def preempt_deduce(self):
        if not self.empty: return
        deducable = {(0, x) for x in range(self.t.side*3)} | {(1, x) for x in range(self.t.side*3)}
        while deducable:
            typ, gx = next(iter(deducable))
            deducable.remove((typ, gx))
            keys = {(1, val, gx) for val in self.vals} if typ else {(0, c) for c in self.t.groups[gx]} 
            keys &= self.empty
            presets = self.preemptive_sets(keys)
            upgroups = set()
            for preset in presets:
                for k in keys:
                    if not self.opts[k] <= preset:
                        for o in preset: 
                            upgroups |= self.removeopt(k, o)
            deducable.update({(typ, ug) for ug in upgroups})
    def assign(self, key, onlyopt):
        upgroups = set()
        if key in self.empty:
            ix, val = (onlyopt, key[1]) if key[0] else (key[1], onlyopt)
            self.board[ix] = val
            if self.opts[key] != 1: self.opts[key] = {onlyopt}
            self.empty.discard((0, ix))
            for group in self.t.cellgroups[ix]:
                for v in (self.vals - {val}): self.removeopt((1, v, group), ix)
                self.empty.discard((1, val, group))
            for cell in self.t.peers[ix]:
                upgroups.update(self.removeassign(cell, val))
        return upgroups
    def removeopt(self, key, opt):
        upgroups = set()
        if opt in self.opts[key]:
            ix = opt if key[0] else key[1]
            upgroups.update(self.t.cellgroups[ix])
            self.opts[key].remove(opt) 
            if len(self.opts[key]) == 1:
                onlyopt = next(iter(self.opts[key]))
                upgroups.update(self.assign(key, onlyopt))
        return upgroups
    def removeassign(self, ix, val):
        upgroups = self.removeopt((0, ix), val)
        for group in self.t.cellgroups[ix]:
            upgroups.update(self.removeopt((1, val, group), ix))
        return upgroups

def solve(p, t):
    d = Deducer(p, t)
    print("#opts pre-deduce:", sum(map(lambda x: len(x), d.opts.values())))
    d.deduce()
    print("#opts post-deduce:", sum(map(lambda x: len(x), d.opts.values())))
    print("Valid" if check(d.board, t) else "Invalid")
    return ''.join(d.board)

def main():
    filename = 'puzzles.txt' if len(sys.argv) == 1 else sys.argv[1]
    puzzles = [line.strip() for line in open(filename)]
    template_size = {}
    start = time.time()
    for ix, p in enumerate(puzzles, start=1):
        if len(p) not in template_size: template_size[len(p)] = template(len(p))
        t = template_size[len(p)]
        print('Puzzle #{}:'.format(ix))
        psolved = solve(p, t)
        print(t.string(p, psolved))
    print("Elapsed time:", time.time()-start)

class template:
    def __init__(self, length):
        self.cells = length
        self.side = int(0.5 + length**0.5)
        self.boxheight, self.boxwidth = nearest_factors(self.side)
        self.groups = [set() for _ in range(self.side*3)]
        for ix in range(self.cells):
            for k, g in enumerate(self._rcb(ix)): self.groups[k*self.side+g].add(ix)
        self.cellgroups = [{k for k in range(len(self.groups)) if i in self.groups[k]} for i in range(self.cells)]
        self.peers = [reduce(lambda a, b: a | b, [self.groups[k] for k in self.cellgroups[i]]) - {i} for i in range(self.cells)]
    def _rcb(self, ix):
        r, c = divmod(ix, self.side)
        return r, c, self.boxheight*(r//self.boxheight) + c//self.boxwidth
    def _string(self, p):
        out = '┌' + (('─'*self.boxwidth+'┬')*self.boxheight)[:-1] + '┐\n'
        breakrow = '├' + (('─'*self.boxwidth+'┼')*self.boxheight)[:-1] + '┤\n'
        row = [str(p[x:x+self.side]) for x in range(0, self.cells, self.side)]
        rowpipe = ['│'+'│'.join([r[x:x+self.boxwidth] for x in range(0, self.side, self.boxwidth)])+'│\n' for r in row]
        out += breakrow.join([''.join(rowpipe[x:x+self.boxheight]) for x in range(0, self.side, self.boxheight)])
        return out + '└' + (('─'*self.boxwidth+'┴')*self.boxheight)[:-1] + '┘\n'
    def string(self, *ps):
        xps = [''.join(map(lambda c: ' ' if c == '.' else c, p)) for p in ps]
        lines = [self._string(p).splitlines() for p in xps]
        return ''.join([' '.join(ls)+'\n' for ls in zip(*lines)])[:-1]

def nearest_factors(num):
    for mul in range(2, num+1):
        lo, hi = mul, num/mul
        if int(hi) != hi: continue
        if lo < hi: continue
        return (int(hi), lo)
def values(s, side):
    values = set(s) - {'.'}
    for ch in "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0":
        if len(values) == side: return values
        if ch not in values: values.add(ch)
def check(p, t):
    for g in t.groups:
        seen = set()
        for cell in g:
            if p[cell] == '.': continue
            if p[cell] in seen: return False
            seen.add(p[cell])
    return True

if __name__ == "__main__": main()