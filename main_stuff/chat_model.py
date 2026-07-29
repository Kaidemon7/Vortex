#!/usr/bin/env python3
import sys, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
adapter_dir = sys.argv[1]
base = sys.argv[2]
tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float32)
model = PeftModel.from_pretrained(model, adapter_dir)
model.eval()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    prompt = f"### Question: {line}\n### Answer:"
    inputs = tokenizer(prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=80, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    full = tokenizer.decode(outputs[0], skip_special_tokens=True)
    parts = full.split("### Answer:")
    if len(parts) >= 2:
        reply = parts[1].strip()
        for stop in ["### Question:", "###"]:
            if stop in reply:
                reply = reply.split(stop)[0].strip()
    else:
        reply = full.strip()
    if not reply: reply = "(no response)"
    print(reply, flush=True)
