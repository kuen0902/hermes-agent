import sys
from datetime import datetime
import pytz

def is_night_session_active():
    """
    Taiwan Night Session Schedule:
    Mon-Fri: 15:00 - 05:00 (next day)
    
    This means:
    - Mon-Fri 15:00-24:00 (Mon, Tue, Wed, Thu, Fri active)
    - Tue-Sat 00:00-06:00 (Tue, Wed, Thu, Fri, Sat active)
    """
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(taipei_tz)
    weekday = now.weekday() # Mon=0, Sun=6
    hour = now.hour

    # Session A: Afternoon/Evening (Mon-Fri 15:00 - 23:59)
    if 0 <= weekday <= 4: # Mon to Fri
        if hour >= 15:
            return True
            
    # Session B: Early Morning (Tue-Sat 00:00 - 05:59)
    if 1 <= weekday <= 5: # Tue to Sat
        if hour < 6:
            return True

    return False

if __name__ == "__main__":
    if is_night_session_active():
        sys.exit(0) # Active
    else:
        sys.exit(1) # Inactive
