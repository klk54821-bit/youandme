#!/bin/bash

echo "🔄 လိုအပ်တဲ့ အခြေခံပစ္စည်းများ သွင်းနေပါသည်..."
# Termux မှာ Python မရှိသေးရင် အရင် install လုပ်မယ်
pkg install python -y

echo "🔄 လိုအပ်တဲ့ Python Library များ သွင်းနေပါသည်..."
# requests, rich စတဲ့ library တွေကို install လုပ်မယ်
pip install requests rich urllib3

echo "⬇️ ကုဒ်များ ဒေါင်းလုဒ်ဆွဲနေပါသည်..."
# သင့်ရဲ့ ဖိုင်နာမည်အတိုင်း ဒီနေရာမှာ ထည့်ထားပါ (V09.py ဖြစ်ပါတယ်)
curl -O https://raw.githubusercontent.com/klk54821-bit/youandme/V09pro.py

echo "✅ အားလုံးအဆင်သင့်ဖြစ်ပါပြီ။"
echo "🚀 စတင်ရန် အောက်ပါ command ကို ရိုက်ပါ -"
echo "python V09pro.py"
