# Bridge Attendance Tracker

A Python application to track bridge players' intentions to participate in bridge games on Thursdays or Fridays of any given month.

## Database Schema

### Month_Year_Thursday_Friday
Stores the schedule for each month:
- `id` - Unique primary key
- `MM` - Month (numeric)
- `YYYY` - Year (numeric)
- `thursdays` - Array of Thursday dates in YYYYMM format
- `fridays` - Array of Friday dates in YYYYMM format

### User
Stores player information and preferences:
- `active` - Boolean, required
- `play_thursdays` - Boolean, required
- `play_fridays` - Boolean, required
- `first` - String, required (first name)
- `last` - String, required (last name)
- `email` - String, required if `prefer_email` is true
- `phone` - String, required and unique
- `first_last_phone_idx` to enforce unique
- `prefer_email` - Boolean, if true, other preference flags are false
- `prefer_phone` - Boolean, if true, other preference flags are false
- `prefer_text` - Boolean, if true, other preference flags are false
- `all_month` - Boolean, true if player attends all month (select_days is false)
- `select_days` - Boolean, true if player selects specific days (all_month is false)
- `will_come` - Boolean
- `will_leave` - Boolean

### Attendance
Tracks actual attendance:
- `MYTF_id` - Foreign key referencing Month_Year_Thursday_Friday table
- `user_id` - Foreign key referencing User table
- `thursdays` - Array of booleans, one for each Thursday in the linked record (if user plays_thursdays is true)
- `fridays` - Array of booleans, one for each Friday in the linked record (if user plays_fridays is true)

## Frontend - DearPyGui

A graphical interface built with DearPyGui providing:

- **CRUD operations** for managing users - trap duplicate user and display 'User exists' message
- **Attendance display/PDF export** showing player attendance by YYYYMM in a data table
  - Number of tables calculated as `mod(sum(attending players, 4))` for each Thursday and Friday
  - **edit attendance records** by first, last, phone for specific YYYYMMDD
- **Filtering** attendance records by YYYYMM and play day (Thursday or Friday)
- **Display & Edit attendance boolean array** for user YYYYMM.
Example:

|User|YYYYMM|Day|1st|2nd|3rd|4th|
|----------|:--------:|:------------:|:-----:|:-----:|:-----:|:-----:|
|B Letson|202602|Thursday|2/06|2/13|2/20|2/27|
||||x|x|x|x|
|B Letson|202602|Friday|2/07|2/14|2/21|2/28|
||||||x|x|

- **Quick attendance updates** for users via phone number or name
  - Prompts to create user record if name or phone not found
- **Automatic schedule management**
  - Triggers to add/delete Month_Year_Thursday_Friday records with associated attendance records
  - **Attendance Reports** by YYYYMM
  - **All User Reports** by active or inactive, by thursdays or fridays or both
  - **Quit** to exit application
