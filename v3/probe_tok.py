import sys,os;sys.path.insert(0,'.');from common import *
import torch
for k in MODELS:
    m,tok,hf=load(k)
    for s in ["7+2=","7-2=","7>2=","? ? ? ?","????","# # # #"," plus"," minus","+","3+4=7\n8-5=3\n"," true"," false","true","false"]:
        print(k,repr(s),[tok.decode([t]) for t in tok.encode(s,add_special_tokens=False)])
    print(k,"layers",m.n_layers, "bos?", m.encode("7+2=")[0].tolist() if hasattr(m,'encode') else None)
    pre="3+4=7\n8-5=3\n6>2=true\n1>7=false\n"
    ok={'add':0,'sub':0,'gt':0};n={'add':0,'sub':0,'gt':0}
    dig=[tok.encode(str(d),add_special_tokens=False)[0] for d in range(10)]
    tf=[tok.encode(w,add_special_tokens=False)[0] for w in ("true","false")]
    for a in range(10):
        for b in range(10):
            for op,f,c in (("+",lambda a,b:a+b,'add'),("-",lambda a,b:a-b,'sub'),(">",lambda a,b:a>b,'gt')):
                r=f(a,b)
                if c!='gt' and not 0<=r<=9: continue
                with torch.no_grad(): lp=hf(input_ids=m.encode(pre+f"{a}{op}{b}=")).logits[0,-1]
                if c=='gt': pred= lp[tf].argmax().item()==(0 if r else 1)
                else: pred=lp[dig].argmax().item()==r
                ok[c]+=pred;n[c]+=1
    print(k,{c:(ok[c]/n[c],n[c]) for c in ok})
