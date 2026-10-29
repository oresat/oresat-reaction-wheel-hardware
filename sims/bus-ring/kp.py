# minimal kicad_pcb s-expr parser -> pickle
import sys, re, pickle
def parse(text):
    tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')
    stack=[[]]
    for m in tok.finditer(text):
        t=m.group(0)
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            if t[0]=='"': t=t[1:-1]
            stack[-1].append(t)
    return stack[0][0]
src=sys.argv[1]; out=sys.argv[2]
tree=parse(open(src).read())
pickle.dump(tree,open(out,'wb'))
