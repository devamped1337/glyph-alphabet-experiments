"""v5k 7B PARTIAL analysis (box-local, post-hoc, written after results). EMBEDDING-LAYER (li=0) channel only. __OVERFLOW__ rows excluded and counted."""
import json,sys,collections,numpy as np
D=sys.argv[1]; L=lambda f: json.load(open(f"{D}/{f}"))
FZ=L("frozen5.json"); BOOK=set(L("book5.json")["books"]["0|pca|0"]["entries"])
OTHER={"qwen7":"olmo7","olmo7":"qwen7"}
def boot(G,n=2000,seed=0):
    G=list(G.values()); 
    if not G: return None
    s=np.array([sum(x) for x in G],float); c=np.array([len(x) for x in G],float)
    i=np.random.default_rng(seed).integers(0,len(G),(n,len(G))); b=s[i].sum(1)/c[i].sum(1)
    return [round(s.sum()/c.sum(),3),round(np.quantile(b,.025),3),round(np.quantile(b,.975),3),int(c.sum()),len(G)]
def acc(rows):
    g={}
    for r in rows: g.setdefault(r["group"],[]).append(0 if r.get("covered")==0 else r.get("correct",0))
    return boot(g)
def paired(A,B):
    ks=set(A)&set(B); g={}
    for k in ks: g.setdefault(A[k][0],[]).append(A[k][1]-B[k][1])
    r=boot(g)
    if not r: return None
    v="equivalent" if r[1]>=-.05 and r[2]<=.05 else "glyph better" if r[1]>0 else "glyph worse" if r[2]<0 else "inconclusive"
    return r+[v]
def slot(r): return {"t4":"place","t5":"status"}.get(r["t"], r["q"] if r["t"]=="t1" else None)
out={"overflow":{}, "tables":{}}
fmt=lambda x:"-" if not x else f"{x[0]:.3f}"
md=[]
for rk in ("qwen7","olmo7"):
    d=L(f"test_{rk}.json"); R0=d["rows"]
    ov=[r for r in R0 if r.get("pred")=="__OVERFLOW__"]
    out["overflow"][rk]={"n":len(ov),"of":len(R0),"by_task":dict(collections.Counter(r["t"]+"|"+r["q"] for r in ov)),"by_cond":dict(collections.Counter(r["cond"] for r in ov))}
    R=[r for r in R0 if r.get("pred")!="__OVERFLOW__" and r["cond"]!="unknown_id_fallback"]
    tasks=FZ["counted"][rk]
    md+=[f"### receiver {rk} (counted tasks {tasks}; overflow rows excluded: {len(ov)}/{len(R0)})","",
         "| task | sender | glyph_id | prose | id_expanded | compact | recv_word_state | none | null_randorth* | null_shufpair* | samenorm_shuf* | raw_unsnapped |","|---|---|---|---|---|---|---|---|---|---|---|---|"]
    pm=["","| task | sender | glyph − prose | glyph − id_expanded | glyph − compact | glyph − recv_word_state |","|---|---|---|---|---|---|"]
    lm=["","| task | sender | LOO all | answer held out | other held out | none |","|---|---|---|---|---|---|"]
    cm=["","| task | glyph_id coverage (gold entry in final book, sender-independent) | cond acc among covered | e2e |","|---|---|---|---|"]
    for tq in tasks:
        t,q=tq.split("|"); T=[r for r in R if r["t"]==t and r["q"]==q]
        sel=lambda c,sk=None,**kw:[r for r in T if r["cond"]==c and (sk is None or r.get("sender")==sk) and all(r.get(a)==b for a,b in kw.items())]
        vec=lambda rows:{(r["mid"],r["q"]):(r["group"],r["correct"]) for r in rows}
        for sk in ("qwen7","olmo7"):
            G=sel("glyph_id",sk,basis="pca",seed=0); cross=(sk!=rk)
            nul=lambda c: fmt(acc(sel(c,sk))) if cross else "n/a(same model)"
            row=[acc(G),acc(sel("text_prose")),acc(sel("id_text_expanded",sk)),acc(sel("text_compact")),acc(sel("receiver_word_state",sk)),acc(sel("none"))]
            md.append(f"| {tq} | {sk} | "+" | ".join(fmt(x) for x in row)+f" | {nul('null_randorth')} | {nul('null_shufpair')} | {nul('glyph_samenorm_shuffled')} | {fmt(acc(sel('glyph_raw_unsnapped',sk)))} |")
            P={bn:paired(vec(G),vec(B)) for bn,B in (("prose",sel("text_prose")),("idexp",sel("id_text_expanded",sk)),("compact",sel("text_compact")),("rws",sel("receiver_word_state",sk)))}
            out["tables"][f"{rk}|{tq}|{sk}"]={"e2e":dict(zip(["glyph_id","prose","id_expanded","compact","rws","none"],row)),"paired":P,
               "nulls":{c:acc(sel(c,sk)) for c in ("null_randorth","null_shufpair","glyph_samenorm_shuffled")} if cross else "same-model: not a null"}
            pm.append(f"| {tq} | {sk} | "+" | ".join("-" if not p else f"{p[0]:+.3f} [{p[1]:+.3f},{p[2]:+.3f}] {p[5]}" for p in P.values())+" |")
            LO=sel("glyph_loo",sk); a=[r for r in LO if r["loo_symbol"]==r["gold"]]; o=[r for r in LO if r["loo_symbol"]!=r["gold"]]
            f2=lambda x:"n/a" if not x else f"{x[0]:.3f} ({x[3]})"
            out["tables"][f"{rk}|{tq}|{sk}"]["loo"]={"all":acc(LO),"answer_held":acc(a),"other_held":acc(o)}
            lm.append(f"| {tq} | {sk} | {f2(acc(LO))} | {f2(acc(a))} | {f2(acc(o))} | {fmt(acc(sel('none')))} |")
        G=sel("glyph_id",None,basis="pca",seed=0); s=slot(T[0])
        if s:
            cov=[r for r in G if f"{t}|{s}|{r['gold']}" in BOOK]
            c=len(cov)/len(G); ca=np.mean([r["correct"] for r in cov]) if cov else float('nan')
            out["tables"][f"{rk}|{tq}|coverage"]={"covered":len(cov),"n":len(G),"cond_acc":ca}
            cm.append(f"| {tq} | {len(cov)}/{len(G)} = {c:.3f} | {ca:.3f} | {np.mean([r['correct'] for r in G]):.3f} |")
    md+=pm+lm+cm+[""]
# DEV by depth (pooled counted tasks, glyph_id)
md+=["### DEV glyph_id by depth (li 0=emb), counted tasks","","| receiver | li=0 | li=1 | li=2 |","|---|---|---|---|"]
for rk in ("qwen7","olmo7"):
    R=[r for r in L(f"dev_{rk}.json")["rows"] if r["cond"]=="glyph_id" and f"{r['t']}|{r['q']}" in FZ["counted"][rk] and r.get("pred")!="__OVERFLOW__"]
    bl={li:acc([r for r in R if r.get("li")==li]) for li in (0,1,2)}; out["tables"][f"dev|{rk}"]=bl
    md.append(f"| {rk} | "+" | ".join(f"{fmt(bl[l])} (n={bl[l][3] if bl[l] else 0})" for l in (0,1,2))+" |")
json.dump(out,open(sys.argv[2]+".json","w"),indent=1,default=float); open(sys.argv[2]+".md","w").write("\n".join(md)); print("\n".join(md)); print(json.dumps(out["overflow"]))
