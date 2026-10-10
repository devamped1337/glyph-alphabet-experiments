import transformers, time
M={"qwen":"Qwen/Qwen2.5-0.5B","smol":"HuggingFaceTB/SmolLM2-360M","pythia":"EleutherAI/pythia-410m"}
W=" Alice Bob Carol Dave Eve Oscar Peggy Alicia Bobby Frank Grace Henry paid called helped thanked warned praised pushed met sent known suspected indeed never before after yes no ? pay call".split(" ")[1:]
for k,n in M.items():
    t=time.time();tok=transformers.AutoTokenizer.from_pretrained(n)
    print(k, {w:len(tok.encode(" "+w,add_special_tokens=False)) for w in W if len(tok.encode(" "+w,add_special_tokens=False))>1}, tok("7-2=")["input_ids"], [tok.decode([x]) for x in tok("Message: It is ? that ? ? ? ?.\n7-2=-5")["input_ids"]], f"{time.time()-t:.0f}s")
hf=transformers.AutoModelForCausalLM.from_pretrained(M["pythia"]); print(hf.config.num_hidden_layers, hf.config.hidden_size)
