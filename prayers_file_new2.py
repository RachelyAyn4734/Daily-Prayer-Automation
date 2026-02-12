import json
from dotenv import load_dotenv
import os
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Save/load the last index from a file
index_file_path = r'C:\Users\user\RunPrayers\last_index.txt'

def save_last_index(index):
    with open(index_file_path, 'w') as f:
        f.write(str(index))

def load_last_index():
    print("index_file_path:",index_file_path)
    try:
        with open(index_file_path, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        print("FileNotFoundError:",ValueError)
        return 0  # Default to 0 if file missing or invalid

# Find the index of a prayer name
def find_index_by_name(name, prayers_dict):
    for index, (prayer_name, _) in prayers_dict.items():
        if prayer_name == name:
            return index
    return -1

# Process and send the next prayer
def process_next_prayer(index, prayers_dict):
    print("process_next_prayer")
    print("index:",index)
    max_prayers_dict=int(max(prayers_dict))
    if 0 < index <= max_prayers_dict:
      
        index_str=str(index)
        name, prayer = prayers_dict[index_str]
        print(f"Processing prayer for: {name} -> {prayer}")
        print("len:",len(prayers_dict)) 
        print("max:",max(prayers_dict)) 
        next_index = index + 1 if index < max_prayers_dict else 1
        # Save the next index for the next run
        save_last_index(next_index)
        return name, prayer
    print("Invalid index")
    return None, None

# Get the next prayer and increment the index
def get_next_prayer(current_index, prayers_dict):
    # Wrap around if we reach the end
    # Assume current_index and prayers_dict are already defined
    max_prayers_dict=int(max(prayers_dict))
    print("max:",max_prayers_dict)
    #next_index = (current_index % ln_prayers_dict) + 1
    if current_index > max_prayers_dict:
    	next_index=1
    else:
        next_index=current_index
    # Loop until we find an existing key in prayers_dict
   
    while str(next_index) not in prayers_dict:
          print("while")
          next_index = next_index  + 1
          if next_index > max_prayers_dict:
             next_index=1
          
        
    # Now, next_index will be the next valid key in prayers_dict or reset to 1
    
    return next_index
    
# Send email
def send_email(prayer, recipient_email):
    load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    hebrew_message = BuildMessage(prayer)
       
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "Today's Prayer Request"
    
    body = f"היום התפילה עבור: {prayer[0]} - {prayer[1]}"
    message.attach(MIMEText(hebrew_message, "html"))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        
def BuildMessage(prayer):
    psalm_text = """
       <div style="text-align:right;">
           <span style="direction:rtl; display:inline-block;">{א} מִזְמוֹר לְדָוִד יְהוָה רֹעִי לֹא אֶחְסָר.</span><br>
           <span style="direction:rtl; display:inline-block;">{ב} בִּנְאוֹת דֶּשֶׁא יַרְבִּיצֵנִי עַל-מֵי מְנֻחוֹת יְנַהֲלֵנִי.</span><br>
           <span style="direction:rtl; display:inline-block;">{ג} נַפְשִׁי יְשׁוֹבֵב יַנְחֵנִי בְמַעְגְּלֵי-צֶדֶק לְמַעַן שְׁמוֹ.</span><br>
           <span style="direction:rtl; display:inline-block;">{ד} גַּם כִּי-אֵלֵךְ בְּגֵיא צַלְמָוֶת לֹא-אִירָא רָע כִּי-אַתָּה עִמָּדִי שִׁבְטְךָ וּמִשְׁעַנְתֶּךָ הֵמָּה יְנַחֲמֻנִי.</span><br>
           <span style="direction:rtl; display:inline-block;">{ה} תַּעֲרֹךְ לְפָנַי שֻׁלְחָן נֶגֶד צֹרְרָי דִּשַּׁנְתָּ בַשֶּׁמֶן רֹאשִׁי כּוֹסִי רְוָיָה.</span><br>
           <span style="direction:rtl; display:inline-block;">{ו} אַךְ טוֹב וָחֶסֶד יִרְדְּפוּנִי כָּל-יְמֵי חַיָּי וְשַׁבְתִּי בְּבֵית-יְהוָה לְאֹרֶךְ יָמִים.</span><br>
       </div>
    """
    hebrew_message = f"""
    <html>
    <body>
       <p style="text-align:right;direction:rtl;">,שלום לכולן<br><br>
       <p style="text-align:right;direction:rtl;">היום מתפללים על  *{prayer[0]} - {prayer[1]}*  :  להצלחה וסיעתא דשמיא במציאת עבודה טובה בקלות ובקרוב <br><br>
            .ובנוסף - לרפואת הפצועים, לשיבת החטופים ולשמירה על החיילים<br><br>
              🙏בואו נעצור לרגע, ונאמר פרק תהלים קצר או נקבל קבלה קטנה <br>
              :לנוחיותכן, מצרפת פרק תהלים שמסוגל לפרנסה טובה<br><br> 
	</p>
	</p>
        <span style="font-size:18px; font-weight:bold; text-align:right; direction:rtl;">*{psalm_text}*</span>
       <p style="text-align:right;direction:rtl;"> <br>
                                    <bdi>
               אם תוכלנה לסמן <span style="color:pink;">❤</span> על ההודעה כדי שאוכל לדעת שהשתתפתן.<br><br>
               תזכו למצוות, מעריכות מאד!<br>
      </bdi>  </p>
    </body>
    </html>
    """
    return hebrew_message


def main():
    parser = argparse.ArgumentParser(description='Process the next prayer by index or by name.')
    parser.add_argument('input', type=str, nargs='?', default=None, help='The index (int) or name (str) of the prayer (optional)')
    
    args = parser.parse_args()
    input_value = args.input

    if input_value:
        try:
            index = int(input_value)
        except ValueError:
            index = find_index_by_name(input_value, prayers_dict)
            index=index+1
            if index == -1:
                print(f"Prayer name '{input_value}' not found.")
                return
    else:
        print("load_last_index")
        index = load_last_index()
    
    with open("prayers.json", "r", encoding="utf-8") as json_file:
         print("open json")
         prayers_dict = json.load(json_file)
  
    print(f"Processing prayer at index: {index}")
    
    # Process the prayer
    name, prayer = process_next_prayer(get_next_prayer(index,prayers_dict), prayers_dict)
    
    if name and prayer:
        send_email((name, prayer), "rachelyayn@gmail.com")

if __name__ == "__main__":
    main()