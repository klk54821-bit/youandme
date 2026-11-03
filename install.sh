#!/bin/bash

echo "🔄 လိုအပ်တဲ့ အခြေခံပစ္စည်းများ သွင်းနေပါသည်..."
pkg install python -y

echo "🔄 လိုအပ်တဲ့ Python Library များ သွင်းနေပါသည်..."
pip install requests rich urllib3

echo "⬇️ ကုဒ်များ ဒေါင်းလုဒ်ဆွဲနေပါသည်..."
# သင့်ဖိုင်နာမည် V09pro.py အတိုင်း သေချာထည့်ထားပါတယ်
curl -O https://raw.githubusercontent.com/klk54821-bit/youandme/main/V09+.py

echo "✅ အားလုံးအဆင်သင့်ဖြစ်ပါပြီ။"
echo "🚀 စတင်ရန် အောက်ပါ command ကို ရိုက်ပါ -"
echo "python V09+.py"
