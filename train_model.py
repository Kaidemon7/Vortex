#!/usr/bin/env python3
import sys, json, os, torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

data_file = sys.argv[1]
out_dir = sys.argv[2]
base = sys.argv[3]
os.makedirs(out_dir, exist_ok=True)
with open(data_file) as f:
    data = json.load(f)
texts = [f"### Question: {item['question']}\n### Answer: {item['answer']}" for item in data]
tokenizer = AutoTokenizer.from_pretrained(base)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float32)
def tokenize(x):
    tok = tokenizer(x["text"], truncation=True, padding="max_length", max_length=256)
    tok["labels"] = tok["input_ids"].copy()
    return tok
dataset = Dataset.from_dict({"text": texts}).map(tokenize)
lora = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj","k_proj","o_proj"], lora_dropout=0.05, task_type=TaskType.CAUSAL_LM)
model = get_peft_model(model, lora)
collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
args = TrainingArguments(output_dir=out_dir, per_device_train_batch_size=1, num_train_epochs=10, logging_steps=1, save_strategy="no", report_to="none", learning_rate=5e-4)
trainer = Trainer(model=model, args=args, train_dataset=dataset, data_collator=collator)
trainer.train()
model.save_pretrained(out_dir)
tokenizer.save_pretrained(out_dir)
print("DONE")
