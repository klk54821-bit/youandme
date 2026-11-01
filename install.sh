#!/bin/bash

echo "🔄 လိုအပ်တဲ့ Library များ သွင်းနေပါသည်..."
pip install requests rich urllib3

echo "⬇️ ကုဒ်များ ဒေါင်းလုဒ်ဆွဲနေပါသည်..."
curl -O https://raw.githubusercontent.com/klk54821-bit/youandme/main/V09pro.py

echo "✅ အားလုံးအဆင်သင့်ဖြစ်ပါပြီ။"
echo "🚀 စတင်ရန် အောက်ပါ command ကို ရိုက်ပါ -"
echo "python V09pro.py"
