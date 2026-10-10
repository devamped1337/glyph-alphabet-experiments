import transformers, torch
name, rev = "allenai/OLMo-2-1124-7B", "7df9a82518afdecae4e8c026b27adccc8c1f0032"
tok = transformers.AutoTokenizer.from_pretrained(name, revision=rev); cfg = transformers.AutoConfig.from_pretrained(name, revision=rev)
cfg.num_hidden_layers, cfg.hidden_size, cfg.intermediate_size, cfg.num_attention_heads, cfg.num_key_value_heads = 8, 256, 512, 4, 4
torch.manual_seed(0); m = transformers.AutoModelForCausalLM.from_config(cfg); m.save_pretrained("smoke/tiny-olmo2"); tok.save_pretrained("smoke/tiny-olmo2"); print(type(m).__name__)
