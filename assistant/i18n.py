"""Fixed reply templates in English, Hindi and Hinglish. Numbers, dates and names are put in by CODE.
The language model may reword the wording, never the numbers (a corrector checks)."""

T = {
 "greet": {
  "en": "Hello! I'm the Ujjwal Rail assistant. I can check trains and seats, your bookings, refunds and rules, and cancel or change a booking after you confirm.",
  "hi": "नमस्ते! मैं उज्ज्वल रेल सहायक हूँ। मैं ट्रेन, सीट, आपकी बुकिंग, रिफंड और नियम बता सकता हूँ, और आपकी पुष्टि के बाद बुकिंग रद्द या बदल सकता हूँ।",
  "hinglish": "Namaste! Main Ujjwal Rail assistant hoon. Main train, seat, aapki booking, refund aur rules bata sakta hoon, aur aapke confirm karne ke baad booking cancel ya change kar sakta hoon."},
 "help": {
  "en": "I can help with train search, seat availability, fares, your booking status, refund estimates, rules, cancelling or changing your own booking, and booking a ticket. What would you like to do?",
  "hi": "मैं ट्रेन खोज, सीट, किराया, बुकिंग की स्थिति, रिफंड का अनुमान, नियम, बुकिंग रद्द/बदलना और टिकट बुक करने में मदद कर सकता हूँ। आप क्या करना चाहेंगे?",
  "hinglish": "Main train search, seat, kiraya, booking status, refund estimate, rules, booking cancel/change aur ticket book karne me madad kar sakta hoon. Aap kya karna chahenge?"},
 "booking_not_found": {
  "en": "I can't find a booking %(bid)s in your account. Please check the booking ID.",
  "hi": "आपके खाते में बुकिंग %(bid)s नहीं मिली। कृपया बुकिंग आईडी जाँच लें।",
  "hinglish": "Aapke account me booking %(bid)s nahi mili. Kripya booking ID check kar lijiye."},
 "other_booking": {
  "en": "I can only help with bookings in your own account, and I can't find %(bid)s there. If it is yours, please sign in with the right account.",
  "hi": "मैं केवल आपके अपने खाते की बुकिंग में मदद कर सकता हूँ, और %(bid)s वहाँ नहीं मिली। अगर यह आपकी है तो सही खाते से साइन-इन करें।",
  "hinglish": "Main sirf aapke apne account ki booking me madad kar sakta hoon, aur %(bid)s wahan nahi mili. Agar yeh aapki hai to sahi account se sign-in kijiye."},
 "ask_booking": {
  "en": "Which booking do you mean? Your bookings: %(list)s. Please tell me the booking ID.",
  "hi": "आप कौन सी बुकिंग की बात कर रहे हैं? आपकी बुकिंग: %(list)s। कृपया बुकिंग आईडी बताइए।",
  "hinglish": "Aap kaun si booking ki baat kar rahe hain? Aapki bookings: %(list)s. Kripya booking ID bataiye."},
 "no_bookings": {
  "en": "You have no bookings yet.", "hi": "आपकी अभी कोई बुकिंग नहीं है।", "hinglish": "Aapki abhi koi booking nahi hai."},
 "ask_search": {
  "en": "Please tell me %(missing)s so I can search trains.",
  "hi": "ट्रेन खोजने के लिए कृपया %(missing)s बताइए।",
  "hinglish": "Train search ke liye kripya %(missing)s bataiye."},
 "m_from": {"en": "where you are travelling from", "hi": "कहाँ से यात्रा करनी है", "hinglish": "kahan se jaana hai"},
 "m_to": {"en": "where you are going", "hi": "कहाँ जाना है", "hinglish": "kahan jaana hai"},
 "m_date": {"en": "the travel date", "hi": "यात्रा की तारीख", "hinglish": "travel ki tareekh"},
 "m_class": {"en": "the class (FP, AC2, AC3, EC, SL or CC)", "hi": "श्रेणी (FP, AC2, AC3, EC, SL या CC)", "hinglish": "class (FP, AC2, AC3, EC, SL ya CC)"},
 "m_train": {"en": "which train number", "hi": "कौन सी ट्रेन (नंबर)", "hinglish": "kaun si train (number)"},
 "m_travellers": {"en": "traveller names and ages, like: Aarav 34, Neha 31", "hi": "यात्रियों के नाम और उम्र, जैसे: Aarav 34, Neha 31", "hinglish": "yatriyon ke naam aur umar, jaise: Aarav 34, Neha 31"},
 "m_newstation": {"en": "the new boarding station", "hi": "नया बोर्डिंग स्टेशन", "hinglish": "naya boarding station"},
 "m_traveller_pick": {"en": "who to cancel (all travellers or a name)", "hi": "किसे रद्द करना है (सभी या कोई नाम)", "hinglish": "kise cancel karna hai (sabhi ya koi naam)"},
 "search_head": {
  "en": "Trains from %(frm)s to %(to)s on %(date)s:", "hi": "%(date)s को %(frm)s से %(to)s की ट्रेनें:", "hinglish": "%(date)s ko %(frm)s se %(to)s ki trains:"},
 "search_none": {
  "en": "I found no train from %(frm)s to %(to)s on %(date)s.", "hi": "%(date)s को %(frm)s से %(to)s की कोई ट्रेन नहीं मिली।", "hinglish": "%(date)s ko %(frm)s se %(to)s ki koi train nahi mili."},
 "search_none_hint": {
  "en": "There is no direct train on that pair. Direct trains from %(frm)s go to: %(a)s. Direct trains to %(to)s start from: %(b)s. You can try a connection through one of them.",
  "hi": "इस जोड़ी पर सीधी ट्रेन नहीं है। %(frm)s से सीधी ट्रेनें यहाँ जाती हैं: %(a)s। %(to)s के लिए सीधी ट्रेनें यहाँ से चलती हैं: %(b)s। इनमें से किसी के रास्ते कनेक्शन आज़मा सकते हैं।",
  "hinglish": "Is pair par seedhi train nahi hai. %(frm)s se seedhi trains yahan jati hain: %(a)s. %(to)s ke liye seedhi trains yahan se chalti hain: %(b)s. Inme se kisi ke raste connection try kar sakte hain."},
 "past_date": {
  "en": "%(date)s has already passed (today is %(today)s). Please give a date from today onwards.",
  "hi": "%(date)s बीत चुकी है (आज %(today)s है)। कृपया आज या उसके बाद की तारीख बताइए।",
  "hinglish": "%(date)s beet chuki hai (aaj %(today)s hai). Kripya aaj ya uske baad ki tareekh bataiye."},
 "midnight_note": {
  "en": "Note: this train leaves %(frm)s after midnight, on %(dep)s, and starts its journey on %(origin)s. Please check which date you mean.",
  "hi": "ध्यान दें: यह ट्रेन %(frm)s से आधी रात के बाद, %(dep)s को चलती है और इसकी यात्रा %(origin)s को शुरू होती है। कृपया सही तारीख देख लें।",
  "hinglish": "Dhyan dein: yeh train %(frm)s se aadhi raat ke baad, %(dep)s ko chalti hai aur iski journey %(origin)s ko shuru hoti hai. Kripya sahi tareekh dekh lein."},
 "status_head": {
  "en": "Booking %(bid)s: %(train)s %(name)s, %(frm)s to %(to)s on %(date)s (%(cls)s). Booking status: %(status)s.",
  "hi": "बुकिंग %(bid)s: ट्रेन %(train)s %(name)s, %(frm)s से %(to)s, %(date)s (%(cls)s)। बुकिंग की स्थिति: %(status)s।",
  "hinglish": "Booking %(bid)s: train %(train)s %(name)s, %(frm)s se %(to)s, %(date)s (%(cls)s). Booking status: %(status)s."},
 "refund_estimate": {
  "en": "If you cancel booking %(bid)s now (%(hours)s before departure from %(frm)s at %(dep)s), you would get back %(refund)s of %(paid)s. %(why)s",
  "hi": "अगर आप बुकिंग %(bid)s अभी रद्द करते हैं (%(frm)s से %(dep)s पर प्रस्थान से %(hours)s पहले), तो %(paid)s में से %(refund)s वापस मिलेंगे। %(why)s",
  "hinglish": "Agar aap booking %(bid)s abhi cancel karte hain (%(frm)s se %(dep)s par departure se %(hours)s pehle), to %(paid)s me se %(refund)s wapas milenge. %(why)s"},
 "why_A": {"en": "More than 48 hours before departure: the fare minus the fixed %(cls)s charge.", "hi": "प्रस्थान से 48 घंटे से अधिक पहले: किराया घटा %(cls)s का निश्चित शुल्क।", "hinglish": "Departure se 48 ghante se zyada pehle: kiraya minus %(cls)s ka fixed charge."},
 "why_B": {"en": "Between 12 and 48 hours before departure: %(pct)s%% of the fare (rounded up to the next ₹5) or the fixed %(cls)s charge, whichever is greater, is deducted.", "hi": "प्रस्थान से 12 से 48 घंटे पहले: किराये का %(pct)s%% (अगले ₹5 तक ऊपर) या निश्चित %(cls)s शुल्क, जो अधिक हो, कटता है।", "hinglish": "Departure se 12 se 48 ghante pehle: kiraye ka %(pct)s%% (agle ₹5 tak upar) ya fixed %(cls)s charge, jo zyada ho, katta hai."},
 "why_C": {"en": "Between 4 and 12 hours before departure: %(pct)s%% of the fare (rounded up to the next ₹5) or the fixed %(cls)s charge, whichever is greater, is deducted.", "hi": "प्रस्थान से 4 से 12 घंटे पहले: किराये का %(pct)s%% (अगले ₹5 तक ऊपर) या निश्चित %(cls)s शुल्क, जो अधिक हो, कटता है।", "hinglish": "Departure se 4 se 12 ghante pehle: kiraye ka %(pct)s%% (agle ₹5 tak upar) ya fixed %(cls)s charge, jo zyada ho, katta hai."},
 "why_D": {"en": "Less than 4 hours before departure: %(pct)s%% of the fare (rounded up to the next ₹5) or the fixed %(cls)s charge, whichever is greater, is deducted.", "hi": "प्रस्थान से 4 घंटे से कम पहले: किराये का %(pct)s%% (अगले ₹5 तक ऊपर) या निश्चित %(cls)s शुल्क, जो अधिक हो, कटता है।", "hinglish": "Departure se 4 ghante se kam pehle: kiraye ka %(pct)s%% (agle ₹5 tak upar) ya fixed %(cls)s charge, jo zyada ho, katta hai."},
 "why_E": {"en": "At or after departure: no voluntary refund.", "hi": "प्रस्थान के समय या बाद में: स्वैच्छिक रद्दीकरण पर कोई रिफंड नहीं।", "hinglish": "Departure ke time ya baad me: voluntary cancellation par refund nahi."},
 "why_OPERATOR": {"en": "Ujjwal Rail cancelled this train, so every fare component is refunded in full without any deduction.", "hi": "उज्ज्वल रेल ने यह ट्रेन रद्द की है, इसलिए बिना किसी कटौती के पूरा किराया वापस होगा।", "hinglish": "Ujjwal Rail ne yeh train cancel ki hai, isliye bina kisi katauti ke poora kiraya wapas hoga."},
 "why_RAC": {"en": "RAC traveller: a fixed charge of %(chg)s per traveller is deducted.", "hi": "RAC यात्री: प्रति यात्री %(chg)s का निश्चित शुल्क कटता है।", "hinglish": "RAC yatri: per yatri %(chg)s ka fixed charge katta hai."},
 "why_WL": {"en": "Waiting-list traveller: a fixed charge of %(chg)s per traveller is deducted.", "hi": "वेटिंग यात्री: प्रति यात्री %(chg)s का निश्चित शुल्क कटता है।", "hinglish": "Waiting list yatri: per yatri %(chg)s ka fixed charge katta hai."},
 "why_TATKAL": {"en": "Confirmed Tatkal travellers get no base-fare refund.", "hi": "कन्फर्म तत्काल यात्रियों को मूल किराये का रिफंड नहीं मिलता।", "hinglish": "Confirmed Tatkal yatriyon ko base fare ka refund nahi milta."},
 "operator_done": {"en": "Booking %(bid)s was cancelled by Ujjwal Rail because the train is not running. You do not need to cancel anything: the full %(refund)s is refunded automatically (card and wallet refunds start within five business days). If it does not arrive, I can pass a dispute to the finance desk.", "hi": "बुकिंग %(bid)s उज्ज्वल रेल ने रद्द की है क्योंकि ट्रेन नहीं चल रही। आपको कुछ रद्द करने की ज़रूरत नहीं: पूरा %(refund)s अपने आप वापस होगा (कार्ड/वॉलेट रिफंड पाँच कार्य-दिवस में शुरू होते हैं)। न मिले तो मैं विवाद फाइनेंस डेस्क को भेज सकता हूँ।", "hinglish": "Booking %(bid)s Ujjwal Rail ne cancel ki hai kyunki train nahi chal rahi. Aapko kuch cancel nahi karna: poora %(refund)s apne aap wapas hoga (card/wallet refund paanch business din me shuru hote hain). Na mile to main dispute finance desk ko bhej sakta hoon."},
 "has_waitlisted": {"en": "Booking %(bid)s has a waiting-list traveller, and a boarding station cannot be changed while any traveller is on the waiting list.", "hi": "बुकिंग %(bid)s में एक वेटिंग यात्री है, और वेटिंग रहते बोर्डिंग स्टेशन नहीं बदला जा सकता।", "hinglish": "Booking %(bid)s me ek waiting list yatri hai, aur waiting rahte boarding station nahi badla ja sakta."},
 "service_cancelled": {"en": "That train service is cancelled on that date, so it cannot be booked.", "hi": "उस तारीख को वह ट्रेन सेवा रद्द है, इसलिए बुक नहीं हो सकती।", "hinglish": "Us tarikh ko woh train service cancel hai, isliye book nahi ho sakti."},
 "too_early_b": {"en": "Booking for that journey opens at 08:00 on %(opens)s (%(days)s days before departure).", "hi": "उस यात्रा की बुकिंग %(opens)s को 08:00 बजे खुलती है (प्रस्थान से %(days)s दिन पहले)।", "hinglish": "Us journey ki booking %(opens)s ko 08:00 baje khulti hai (departure se %(days)s din pehle)."},
 "closed_b": {"en": "Booking for that train closed %(mins)s minutes before it leaves its first station.", "hi": "उस ट्रेन की बुकिंग पहले स्टेशन से छूटने से %(mins)s मिनट पहले बंद हो गई।", "hinglish": "Us train ki booking pehle station se chhootne se %(mins)s minute pehle band ho gayi."},
 "confirm_cancel": {
  "en": "Preview (nothing has changed yet): cancel booking %(bid)s for %(who)s. Refund %(refund)s of %(paid)s. %(why)s Press Confirm within %(mins)s minutes to go ahead, or Cancel to keep the booking.",
  "hi": "पूर्वावलोकन (अभी कुछ नहीं बदला): बुकिंग %(bid)s %(who)s के लिए रद्द होगी। %(paid)s में से %(refund)s रिफंड। %(why)s आगे बढ़ने के लिए %(mins)s मिनट में Confirm दबाइए, या बुकिंग रखने के लिए Cancel दबाइए।",
  "hinglish": "Preview (abhi kuch nahi badla): booking %(bid)s %(who)s ke liye cancel hogi. %(paid)s me se %(refund)s refund. %(why)s Aage badhne ke liye %(mins)s minute me Confirm dabaiye, ya booking rakhne ke liye Cancel dabaiye."},
 "confirm_change": {
  "en": "Preview (nothing has changed yet): change the boarding station of booking %(bid)s from %(old)s to %(new)s. The new departure is %(dep)s and the fare stays the same. You can change up to %(hours)s hours before departure (%(src)s). Press Confirm within %(mins)s minutes, or Cancel.",
  "hi": "पूर्वावलोकन (अभी कुछ नहीं बदला): बुकिंग %(bid)s का बोर्डिंग स्टेशन %(old)s से %(new)s होगा। नया प्रस्थान %(dep)s और किराया वही रहेगा। आप प्रस्थान से %(hours)s घंटे पहले तक बदल सकते हैं (%(src)s)। %(mins)s मिनट में Confirm दबाइए, या Cancel।",
  "hinglish": "Preview (abhi kuch nahi badla): booking %(bid)s ka boarding station %(old)s se %(new)s hoga. Naya departure %(dep)s aur kiraya wahi rahega. Aap departure se %(hours)s ghante pehle tak badal sakte hain (%(src)s). %(mins)s minute me Confirm dabaiye, ya Cancel."},
 "confirm_book": {
  "en": "Preview (nothing is booked yet): train %(train)s, %(frm)s to %(to)s, %(cls)s, departing %(dep)s. Travellers: %(who)s. Total %(total)s. Press Confirm within %(mins)s minutes to book, or Cancel.",
  "hi": "पूर्वावलोकन (अभी कुछ बुक नहीं हुआ): ट्रेन %(train)s, %(frm)s से %(to)s, %(cls)s, प्रस्थान %(dep)s। यात्री: %(who)s। कुल %(total)s। बुक करने के लिए %(mins)s मिनट में Confirm दबाइए, या Cancel।",
  "hinglish": "Preview (abhi kuch book nahi hua): train %(train)s, %(frm)s se %(to)s, %(cls)s, departure %(dep)s. Yatri: %(who)s. Total %(total)s. Book karne ke liye %(mins)s minute me Confirm dabaiye, ya Cancel."},
 "done_cancel": {
  "en": "Done. Booking %(bid)s: %(n)s traveller(s) cancelled. Refund %(refund)s. Booking status is now %(status)s. (I re-read the booking to check.)",
  "hi": "हो गया। बुकिंग %(bid)s: %(n)s यात्री रद्द। रिफंड %(refund)s। बुकिंग की स्थिति अब %(status)s है। (मैंने बुकिंग दोबारा पढ़कर जाँच की।)",
  "hinglish": "Ho gaya. Booking %(bid)s: %(n)s yatri cancel. Refund %(refund)s. Booking status ab %(status)s hai. (Maine booking dobara padhkar check ki.)"},
 "done_change": {
  "en": "Done. Booking %(bid)s now boards at %(new)s (was %(old)s). (I re-read the booking to check.)",
  "hi": "हो गया। बुकिंग %(bid)s अब %(new)s से चढ़ेगी (पहले %(old)s)। (मैंने बुकिंग दोबारा पढ़कर जाँच की।)",
  "hinglish": "Ho gaya. Booking %(bid)s ab %(new)s se chadhegi (pehle %(old)s). (Maine booking dobara padhkar check ki.)"},
 "done_book": {
  "en": "Booked. Booking %(bid)s, status %(status)s, total %(total)s. (I re-read the booking to check.)",
  "hi": "बुक हो गया। बुकिंग %(bid)s, स्थिति %(status)s, कुल %(total)s। (मैंने दोबारा पढ़कर जाँच की।)",
  "hinglish": "Book ho gaya. Booking %(bid)s, status %(status)s, total %(total)s. (Maine dobara padhkar check kiya.)"},
 "already_done": {
  "en": "This was already done earlier, so I changed nothing now.", "hi": "यह पहले ही हो चुका है, इसलिए अभी कुछ नहीं बदला।", "hinglish": "Yeh pehle hi ho chuka hai, isliye abhi kuch nahi badla."},
 "expired": {
  "en": "That preview has expired, so nothing was changed. Ask me again and I will show a fresh preview.", "hi": "वह पूर्वावलोकन समाप्त हो गया, इसलिए कुछ नहीं बदला। दोबारा कहिए, मैं नया पूर्वावलोकन दिखाऊँगा।", "hinglish": "Woh preview expire ho gaya, isliye kuch nahi badla. Dobara bataiye, main naya preview dikhaunga."},
 "quote_changed": {
  "en": "The refund changed since the preview (it was %(old)s, now it would be %(new)s), so I did not cancel. Please ask again for a fresh preview.",
  "hi": "पूर्वावलोकन के बाद रिफंड बदल गया (पहले %(old)s, अब %(new)s), इसलिए मैंने रद्द नहीं किया। कृपया नया पूर्वावलोकन माँगिए।",
  "hinglish": "Preview ke baad refund badal gaya (pehle %(old)s, ab %(new)s), isliye maine cancel nahi kiya. Kripya naya preview maangiye."},
 "action_cancelled": {
  "en": "Okay, I did not change anything.", "hi": "ठीक है, मैंने कुछ नहीं बदला।", "hinglish": "Theek hai, maine kuch nahi badla."},
 "action_gone": {
  "en": "I can't find that pending action.", "hi": "वह लंबित कार्रवाई नहीं मिली।", "hinglish": "Woh pending action nahi mila."},
 "action_failed": {
  "en": "I could not complete that (%(why)s). Nothing was changed.", "hi": "मैं यह पूरा नहीं कर सका (%(why)s)। कुछ नहीं बदला।", "hinglish": "Main yeh poora nahi kar saka (%(why)s). Kuch nahi badla."},
 "pending_hint": {
  "en": "You have a preview waiting (%(aid)s). Please use the Confirm or Cancel button (a separate step) so I know it is really you deciding.",
  "hi": "आपका एक पूर्वावलोकन लंबित है (%(aid)s)। कृपया Confirm या Cancel बटन दबाइए (यह अलग चरण है)।",
  "hinglish": "Aapka ek preview pending hai (%(aid)s). Kripya Confirm ya Cancel button dabaiye (yeh alag step hai)."},
 "too_late_change": {
  "en": "Sorry, the last time to change the boarding station for booking %(bid)s was %(deadline)s (%(hours)s hours before the train leaves its first station, %(src)s). I can't change it now.",
  "hi": "क्षमा करें, बुकिंग %(bid)s का बोर्डिंग स्टेशन बदलने का अंतिम समय %(deadline)s था (प्रस्थान से %(hours)s घंटे पहले, %(src)s)। अब मैं इसे नहीं बदल सकता।",
  "hinglish": "Maaf kijiye, booking %(bid)s ka boarding station badalne ka last time %(deadline)s tha (departure se %(hours)s ghante pehle, %(src)s). Ab main ise nahi badal sakta."},
 "bad_station": {
  "en": "The new boarding station must be a later stop on the same train, before your destination.", "hi": "नया बोर्डिंग स्टेशन उसी ट्रेन का आगे वाला स्टॉप होना चाहिए, आपके गंतव्य से पहले।", "hinglish": "Naya boarding station usi train ka aage wala stop hona chahiye, aapki destination se pehle."},
 "already_changed": {
  "en": "The boarding station of this booking was already changed once, and only one change is allowed.", "hi": "इस बुकिंग का बोर्डिंग स्टेशन एक बार बदला जा चुका है, केवल एक बदलाव की अनुमति है।", "hinglish": "Is booking ka boarding station ek baar badla ja chuka hai, sirf ek change allowed hai."},
 "not_active": {
  "en": "Booking %(bid)s is already cancelled, so there is nothing to change.", "hi": "बुकिंग %(bid)s पहले ही रद्द है, इसलिए बदलने को कुछ नहीं है।", "hinglish": "Booking %(bid)s pehle hi cancel hai, isliye badalne ko kuch nahi hai."},
 "departed": {
  "en": "That train has already left, so I can't do this.", "hi": "वह ट्रेन जा चुकी है, इसलिए मैं यह नहीं कर सकता।", "hinglish": "Woh train ja chuki hai, isliye main yeh nahi kar sakta."},
 "regret": {
  "en": "No seats or waiting-list places are left in that class on that day.", "hi": "उस दिन उस श्रेणी में कोई सीट या वेटिंग जगह नहीं बची है।", "hinglish": "Us din us class me koi seat ya waiting list jagah nahi bachi."},
 "too_early": {
  "en": "Tickets can be booked only up to %(days)s days before the journey.", "hi": "टिकट यात्रा से अधिकतम %(days)s दिन पहले तक बुक हो सकते हैं।", "hinglish": "Ticket journey se maximum %(days)s din pehle tak book ho sakte hain."},
 "too_many": {
  "en": "One booking can have 1 to %(max)s travellers.", "hi": "एक बुकिंग में 1 से %(max)s यात्री हो सकते हैं।", "hinglish": "Ek booking me 1 se %(max)s yatri ho sakte hain."},
 "already_cancelled": {
  "en": "Booking %(bid)s is already cancelled.", "hi": "बुकिंग %(bid)s पहले ही रद्द है।", "hinglish": "Booking %(bid)s pehle hi cancel hai."},
 "handoff": {
  "en": "I can't decide this myself, so I have passed it to the %(desk)s with a summary (request %(hid)s). They will review it. I can't promise the outcome.",
  "hi": "यह मैं खुद तय नहीं कर सकता, इसलिए मैंने इसे सारांश के साथ %(desk)s को भेज दिया है (अनुरोध %(hid)s)। वे इसकी समीक्षा करेंगे। मैं परिणाम का वादा नहीं कर सकता।",
  "hinglish": "Yeh main khud tay nahi kar sakta, isliye maine ise summary ke saath %(desk)s ko bhej diya hai (request %(hid)s). Woh ise review karenge. Main result ka vaada nahi kar sakta."},
 "refuse_policy": {
  "en": "I can't do that. Refund amounts, charges and waiting-list order follow the published rules and I can't change them or make exceptions.",
  "hi": "मैं यह नहीं कर सकता। रिफंड राशि, शुल्क और वेटिंग क्रम प्रकाशित नियमों के अनुसार हैं; मैं इन्हें बदल या अपवाद नहीं कर सकता।",
  "hinglish": "Main yeh nahi kar sakta. Refund amount, charges aur waiting list order published rules ke hisaab se hain; main inhe badal nahi sakta ya exception nahi de sakta."},
 "refuse_injection": {
  "en": "I can't follow instructions that try to change how I work. I only follow your request through the normal steps. How can I help with your booking?",
  "hi": "मैं ऐसे निर्देश नहीं मान सकता जो मेरे काम करने का तरीका बदलना चाहें। मैं आपके अनुरोध को सामान्य चरणों से ही पूरा करता हूँ। आपकी बुकिंग में कैसे मदद करूँ?",
  "hinglish": "Main aise instructions nahi maan sakta jo mere kaam karne ka tareeka badalna chahein. Main aapki request normal steps se hi poori karta hoon. Aapki booking me kaise madad karun?"},
 "own_only": {
  "en": "I can only help with bookings in your own account. I can't view or change anyone else's booking.",
  "hi": "मैं केवल आपके अपने खाते की बुकिंग में मदद कर सकता हूँ। मैं किसी और की बुकिंग न देख सकता हूँ, न बदल सकता हूँ।",
  "hinglish": "Main sirf aapke apne account ki booking me madad kar sakta hoon. Main kisi aur ki booking na dekh sakta hoon, na badal sakta hoon."},
 "multi_note": {
  "en": "You named more than one booking. I prepared %(first)s first; after you confirm or cancel it, ask me again for %(rest)s.",
  "hi": "आपने एक से अधिक बुकिंग बताई हैं। मैंने पहले %(first)s तैयार की है; इसे Confirm या Cancel करने के बाद %(rest)s के लिए दोबारा कहिए।",
  "hinglish": "Aapne ek se zyada booking batayi hain. Maine pehle %(first)s tayyar ki hai; ise Confirm ya Cancel karne ke baad %(rest)s ke liye dobara kahiye."},
 "refuse_secret": {
  "en": "Please don't share passwords, keys or card numbers here. I never need them.", "hi": "कृपया यहाँ पासवर्ड, कुंजी या कार्ड नंबर साझा न करें। मुझे इनकी ज़रूरत नहीं।", "hinglish": "Kripya yahan password, key ya card number share na karein. Mujhe inki zaroorat nahi."},
 "refuse_privacy": {
  "en": "I can't share personal details like full phone or ID numbers.", "hi": "मैं पूरा फ़ोन या आईडी नंबर जैसी निजी जानकारी नहीं बता सकता।", "hinglish": "Main poora phone ya ID number jaisi personal details nahi bata sakta."},
 "rules_not_found": {
  "en": "I could not find this in our rules, circulars or FAQs, so I won't guess. I can pass it to a human desk if you like.",
  "hi": "यह मुझे हमारे नियमों, परिपत्रों या FAQ में नहीं मिला, इसलिए मैं अंदाज़ा नहीं लगाऊँगा। चाहें तो मैं इसे मानव डेस्क को भेज दूँ।",
  "hinglish": "Yeh mujhe hamare rules, circulars ya FAQ me nahi mila, isliye main andaza nahi lagaunga. Chahein to main ise human desk ko bhej dun."},
 "rules_prefix": {"en": "According to %(src)s:", "hi": "%(src)s के अनुसार:", "hinglish": "%(src)s ke according:"},
 "upcoming_note": {
  "en": "Note: a newer circular, %(doc)s, takes effect on %(date)s and will change this.", "hi": "ध्यान दें: नया परिपत्र %(doc)s %(date)s से लागू होगा और इसे बदल देगा।", "hinglish": "Dhyan dein: naya circular %(doc)s %(date)s se lagu hoga aur ise badal dega."},
 "overridden_note": {
  "en": "Some older or less official pages (%(docs)s) say something different; I followed the higher-authority, newer source.", "hi": "कुछ पुराने या कम आधिकारिक पृष्ठ (%(docs)s) कुछ और कहते हैं; मैंने अधिक आधिकारिक, नए स्रोत का पालन किया।", "hinglish": "Kuch purane ya kam official pages (%(docs)s) kuch aur kehte hain; maine zyada official, naye source ko follow kiya."},
 "deadline_change": {
  "en": "You can change the boarding station of booking %(bid)s until %(deadline)s (%(hours)s hours before the train leaves its first station, %(src)s).", "hi": "आप बुकिंग %(bid)s का बोर्डिंग स्टेशन %(deadline)s तक बदल सकते हैं (प्रस्थान से %(hours)s घंटे पहले, %(src)s)।", "hinglish": "Aap booking %(bid)s ka boarding station %(deadline)s tak badal sakte hain (departure se %(hours)s ghante pehle, %(src)s)."},
 "deadline_refund": {
  "en": "For booking %(bid)s (departure %(dep)s): until %(a)s only the fixed class charge is deducted; until %(b)s %(pb)s%% (or the fixed charge if greater) is deducted; until %(c)s %(pc)s%%; after that %(pd)s%% until departure; at or after departure there is no refund.",
  "hi": "बुकिंग %(bid)s (प्रस्थान %(dep)s): %(a)s तक केवल निश्चित शुल्क कटता है; %(b)s तक %(pb)s%% (या निश्चित शुल्क, जो अधिक हो); %(c)s तक %(pc)s%%; उसके बाद प्रस्थान तक %(pd)s%%; प्रस्थान के समय या बाद में कोई रिफंड नहीं।",
  "hinglish": "Booking %(bid)s (departure %(dep)s): %(a)s tak sirf fixed class charge katta hai; %(b)s tak %(pb)s%% (ya fixed charge agar zyada ho); %(c)s tak %(pc)s%%; uske baad departure tak %(pd)s%%; departure ke time ya baad me refund nahi."},
 "ambiguous_station": {"en": "%(place)s has more than one station: %(options)s. Which one do you mean? Please say the full station name or its code.", "hi": "%(place)s में एक से ज़्यादा स्टेशन हैं: %(options)s। आपका मतलब कौन सा है? कृपया पूरा नाम या कोड बताएँ।", "hinglish": "%(place)s me ek se zyada station hain: %(options)s. Aapka matlab kaun sa hai? Kripya poora naam ya code batayein."},
 "unknown_place": {"en": "I could not find a station called %(place)s in the Ujjwal Rail network. We serve: %(cities)s. Where would you like to travel from and to?", "hi": "उज्ज्वल रेल नेटवर्क में %(place)s नाम का स्टेशन नहीं मिला। हम इन शहरों को जोड़ते हैं: %(cities)s। आप कहाँ से कहाँ जाना चाहते हैं?", "hinglish": "Ujjwal Rail network me %(place)s naam ka station nahi mila. Hum in shehron ko jodte hain: %(cities)s. Aap kahan se kahan jaana chahte hain?"},
 "unknown": {
  "en": "I'm not sure I understood. Could you rephrase? For example: \"trains from Anandpur to Chetakgarh tomorrow\" or \"cancel booking BKG0001\".",
  "hi": "मुझे पूरी तरह समझ नहीं आया। क्या आप दोबारा कह सकते हैं? जैसे: \"कल आनंदपुर से चेतकगढ़ की ट्रेनें\" या \"बुकिंग BKG0001 रद्द करो\"।",
  "hinglish": "Mujhe poori tarah samajh nahi aaya. Kya aap dobara keh sakte hain? Jaise: \"kal Anandpur se Chetakgarh ki trains\" ya \"booking BKG0001 cancel karo\"."},
 "gave_up": {
  "en": "I still don't have enough to go ahead (%(missing)s). I'll pass this to a human desk who can take the details.",
  "hi": "आगे बढ़ने के लिए अब भी जानकारी कम है (%(missing)s)। मैं इसे मानव डेस्क को भेज देता हूँ जो विवरण ले सकते हैं।",
  "hinglish": "Aage badhne ke liye ab bhi jaankari kam hai (%(missing)s). Main ise human desk ko bhej deta hoon jo details le sakte hain."},
 "ingest_ok": {"en": "Added and live.", "hi": "जोड़ दिया गया और लाइव है।", "hinglish": "Add ho gaya aur live hai."},
}

STATUS_NAMES = {
    "CONFIRMED": {"en": "confirmed", "hi": "कन्फर्म", "hinglish": "confirmed"},
    "RAC": {"en": "RAC", "hi": "RAC", "hinglish": "RAC"},
    "WAITLISTED": {"en": "waiting list", "hi": "वेटिंग लिस्ट", "hinglish": "waiting list"},
    "MIXED": {"en": "mixed (travellers have different statuses)", "hi": "मिश्रित (यात्रियों की स्थिति अलग-अलग)", "hinglish": "mixed (yatriyon ka status alag-alag)"},
    "CANCELLED": {"en": "cancelled", "hi": "रद्द", "hinglish": "cancelled"},
    "OPERATOR_CANCELLED": {"en": "train cancelled by Ujjwal Rail", "hi": "उज्ज्वल रेल द्वारा ट्रेन रद्द", "hinglish": "Ujjwal Rail ne train cancel ki"},
}


def t(key: str, lang: str, **kw) -> str:
    tmpl = T[key].get(lang) or T[key]["en"]
    return tmpl % kw if kw else tmpl


def status_name(status: str, lang: str) -> str:
    return STATUS_NAMES.get(status, {}).get(lang) or status
