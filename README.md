# Financial Consolidator

A Django application for managing financial data consolidation across multiple companies and accounts with **hierarchical reporting capabilities**.

## Features

- **Company Management**: Manage multiple companies with unique codes
- **Chart of Accounts Management**: Upload, view, and manage hierarchical chart of accounts
- **Chart of Accounts View**: Browse all accounts with search, hierarchical display, and export functionality
- **Account Management**: Organize accounts by type (Asset, Liability, Equity, Revenue, Expense)
- **Financial Data**: Store and manage financial data with different types (Actual, Budget, Forecast)
- **Hierarchical P&L Reports**: Generate profit and loss reports with automatic grouping by Parent Category and Sub Category, including calculated totals (Gross Profit, Net Profit Before Tax, Net Profit After Tax)
- **Hierarchical Balance Sheet Reports**: Generate balance sheet reports with automatic grouping by Parent Category and Sub Category, including calculated totals and balance check
- **Data Backup & Restore**: Automatic backup functionality before overwriting financial data
- **Admin Interface**: Full Django admin interface for data management

## Models

### Company
- `name`: Company name
- `code`: Unique company code

### Account
- `code`: Unique account code
- `name`: Account name
- `type`: Account type (Asset, Liability, Equity, Revenue, Expense)

### FinancialData
- `company`: Foreign key to Company
- `account`: Foreign key to Account
- `period`: Date field for the financial period
- `amount`: Decimal field for the financial amount
- `data_type`: Type of data (Actual, Budget, Forecast)

### ChartOfAccounts
- `account_code`: Unique account code
- `account_name`: Account name
- `account_type`: Account type (INCOME, EXPENSE, ASSET, LIABILITY, EQUITY)
- `category`: Category for subtotals (e.g., GROSS_PROFIT, REVENUE)
- `formula`: Optional formula for calculated fields

## Setup Instructions

### Prerequisites

1. **Python 3.8+**
2. **PostgreSQL** (version 12 or higher)
3. **pip** (Python package installer)

### Installation

1. **Clone the repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd financial_consolidator
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Database Setup

1. **Install PostgreSQL** (if not already installed):
   - **macOS**: `brew install postgresql`
   - **Ubuntu/Debian**: `sudo apt-get install postgresql postgresql-contrib`
   - **Windows**: Download from https://www.postgresql.org/download/windows/

2. **Start PostgreSQL service**:
   - **macOS**: `brew services start postgresql`
   - **Ubuntu/Debian**: `sudo systemctl start postgresql`
   - **Windows**: Start from Services or use pgAdmin

3. **Create database and user**:
   ```bash
   # Connect to PostgreSQL as superuser
   psql -U postgres
   
   # Create database
   CREATE DATABASE consolidator_db;
   
   # Create user (if needed)
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE consolidator_db TO postgres;
   
   # Exit psql
   \q
   ```

4. **Update database settings** (if needed):
   Edit `financial_consolidator/settings.py` and update the DATABASES configuration:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'consolidator_db',
           'USER': 'postgres',
           'PASSWORD': 'your_password_here',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

### Django Setup

1. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

2. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create your admin user.

3. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

4. **Access the application**:
   - Admin interface: http://127.0.0.1:8000/admin/
   - Main site: http://127.0.0.1:8000/

## Usage

### Admin Interface

1. Log in to the admin interface at http://127.0.0.1:8000/admin/
2. Use the superuser credentials you created
3. Manage Companies, Accounts, and Financial Data through the admin interface

### Adding Data

1. **Add Companies**: Go to Companies section and add company records
2. **Add Accounts**: Go to Accounts section and add account records with appropriate types
3. **Add Financial Data**: Go to Financial Data section and add financial records linking companies and accounts
4. **Upload Chart of Accounts**: Use the upload functionality at `/upload/chart-of-accounts/` to bulk import account structures

### Chart of Accounts Management

#### View Chart of Accounts
The application includes a comprehensive view for browsing and managing Chart of Accounts:

1. **Access View Page**: Navigate to `/chart-of-accounts/`
2. **Browse Accounts**: View all accounts in hierarchical structure
3. **Search Functionality**: Use the search box to filter accounts by:
   - Account Code
   - Account Name
   - Account Type
   - Parent Category
   - Sub Category
4. **Export Options**: 
   - Export to CSV: Download as CSV file
   - Export to Excel: Download as Excel file
5. **Hierarchical Display**: Accounts are displayed with proper indentation for sub-categories
6. **Account Information**: View Sort Order, Account Code, Account Name, Type, Parent Category, and Sub Category

#### Upload Chart of Accounts

The application includes a bulk upload feature for Chart of Accounts:

1. **Access Upload Page**: Navigate to `/upload/chart-of-accounts/`
2. **Download Template**: Click "Download Template" to get a sample CSV file
3. **Prepare Your Data**: Fill in the template with your account data
4. **Upload File**: Select your CSV/Excel file and click "Upload Chart of Accounts"

**Required Columns:**
- Sort Order (numeric, required)
- Account Code (can be empty for header rows, duplicates checked during upload)
- Account Name (required, max 200 characters)
- Type (INCOME, EXPENSE, ASSET, LIABILITY, EQUITY, optional, max 100 characters)
- Parent Category (optional, for main groupings, max 200 characters)
- Sub Category (optional, for subgroupings, max 200 characters)

**Replace Option:**
- **Checkbox**: "Replace all existing Chart of Accounts data"
- **Function**: Deletes all existing Chart of Accounts before importing new data
- **Safety**: Financial data remains intact, only Chart of Accounts are affected
- **Warning**: Clear warning message before deletion

**Supported File Formats:** CSV, Excel (.xlsx, .xls)

### Financial Data Upload

The application includes a bulk upload feature for Financial Data:

1. **Access Upload Page**: Navigate to `/upload/financial-data/`
2. **Download Template**: Click "Download Template" to get a sample Excel file
3. **Select Parameters**: Choose Company and Data Type (Actual/Budget/Forecast)
4. **Dynamic Period Detection**: System automatically detects periods from column headers (Jan-24, Feb-24, etc.)
5. **Number Format Support**: Handles various number formats including commas, parentheses for negatives, and text formatting
6. **Automatic Backup**: Creates backup of existing data before overwriting
7. **Overwrite Confirmation**: Shows warning for existing data and confirms overwrite action
4. **Prepare Your Data**: Fill in the template with your financial data
5. **Upload File**: Select your Excel file and click "Upload Financial Data"
6. **Automatic Detection**: System automatically detects periods from column headers

**File Structure:**
- **Column A**: Account Code (required)
- **Columns B onwards**: Period data (e.g., Jan-24, Feb-24, Mar-24)

**Number Format Support:**
The system automatically handles various Excel number formats:
- **Regular numbers**: 1234.56, 1,234.56
- **Text-formatted numbers**: '26,660.86', "1,234.56"
- **Negative numbers**: -1234.56, (1,234.56)
- **Numbers with spaces**: " 1,234.56 "
- **Empty cells**: Automatically skipped
- **Large numbers**: 1,000,000, 1,234,567.89

**Parameters:**
- **Company**: Select from existing companies
- **Data Type**: Actual, Budget, or Forecast

**Period Format:** Multiple formats supported:
- **Mon-YY**: Jan-24, Feb-25, Mar-24
- **YY-Mon**: 24-Jan, 25-Feb, 24-Mar
- **Month YYYY**: January 2024, Feb 2025, March 2024
- **MM/YYYY**: 01/2024, 12/2025, 03/2024
- **YYYY-MM**: 2024-01, 2025-12, 2024-03

**Year Interpretation**: YY is interpreted as 20YY (24 = 2024, 25 = 2025)
**Year Range**: Supported years: 2020-2099
**Flexibility**: Upload any period range - single month or multiple years
**Overwrite Protection**: System warns if data exists for same periods and overwrites existing records
**Automatic Backup**: Creates backup of existing data before overwriting, restorable from Admin panel
**Number Parsing**: Handles various Excel number formats including text-formatted numbers, commas, parentheses for negatives
**Supported File Formats:** Excel (.xlsx, .xls), CSV

## Data Backup & Restore

The application includes automatic backup functionality to protect against data loss:

### Automatic Backup
- **When**: Before overwriting existing financial data
- **What**: All existing records for the company and data type
- **Storage**: JSON format in DataBackup model
- **Access**: Admin panel > Data Backups

### Backup Features
- **Automatic Creation**: Backups are created automatically before data overwrites
- **User Tracking**: Records which user made the upload
- **Period Information**: Shows which periods were backed up
- **Description**: Auto-generated description with timestamp

### Restore Functionality
- **Admin Access**: Available in Admin panel under "Data Backups"
- **Restore Button**: One-click restore for each backup
- **Safety**: Creates backup of current data before restoring
- **Complete Restore**: Restores all records from the backup

### Backup Information
- **Backup Date**: When the backup was created
- **Company**: Which company's data was backed up
- **Data Type**: Actual, Budget, or Forecast
- **Periods**: List of periods that were backed up
- **User**: Who made the upload that triggered the backup

## Hierarchical Reports

The application includes **advanced hierarchical reporting capabilities** that automatically group accounts by Parent Category and Sub Category, providing professional financial statements with calculated totals.

### Hierarchical P&L Report
- **URL**: `/reports/pl/`
- **Hierarchical Structure**:
  - **Parent Categories**: INCOME, COST OF FUNDS, OVERHEADS, TAXES
  - **Sub Categories**: Interest Income, Fee Income, Salaries, Marketing, etc.
  - **Individual Accounts**: Detailed account lines within each sub-category
  - **Automatic Subtotals**: Calculated for each sub-category
  - **Parent Totals**: Calculated for each parent category
  - **Calculated Totals**: 
    - **GROSS PROFIT**: TOTAL INCOME - TOTAL COST OF FUNDS
    - **NET PROFIT BEFORE TAX**: GROSS PROFIT - TOTAL OVERHEADS
    - **NET PROFIT AFTER TAX**: NET PROFIT BEFORE TAX - TAXES

- **Visual Features**:
  - **Color-coded Sections**: Different background colors for headers, subtotals, and totals
  - **Indentation**: Clear visual hierarchy with proper indentation
  - **Bold Formatting**: Headers and totals displayed in bold
  - **Company Columns**: F2001 (light blue), GL001 (light green), TOTAL (light gray)
  - **DataTables Integration**: Fixed columns, scrolling, no sorting to preserve hierarchy
  - **Responsive Design**: Works on all screen sizes

### Hierarchical Balance Sheet Report
- **URL**: `/reports/bs/`
- **Hierarchical Structure**:
  - **Parent Categories**: ASSETS, LIABILITIES, EQUITY
  - **Sub Categories**: Current Assets, Fixed Assets, Current Liabilities, etc.
  - **Individual Accounts**: Detailed account lines within each sub-category
  - **Automatic Subtotals**: Calculated for each sub-category
  - **Parent Totals**: Calculated for each parent category
  - **Balance Check**: TOTAL ASSETS - TOTAL LIABILITIES - TOTAL EQUITY (should equal 0)

- **Visual Features**:
  - **Color-coded Sections**: Different background colors for headers, subtotals, and totals
  - **Indentation**: Clear visual hierarchy with proper indentation
  - **Bold Formatting**: Headers and totals displayed in bold
  - **Company Columns**: F2001 (light blue), GL001 (light green), TOTAL (light gray)
  - **DataTables Integration**: Fixed columns, scrolling, no sorting to preserve hierarchy
  - **Responsive Design**: Works on all screen sizes

### Report Features
- **Period Filtering**: From/To month and year selectors
- **Data Type Filtering**: Actual, Budget, Forecast
- **Export to Excel**: Download reports in Excel format
- **Print Functionality**: Print-friendly reports
- **Navigation Menu**: Easy switching between P&L and Balance Sheet
- **Debug Information**: Detailed troubleshooting information when no data is found
  - Print functionality
  - **Sticky Headers**: Account Code and Account Name columns stay fixed when scrolling horizontally
  - **Sticky Period Headers**: Period headers stay fixed when scrolling vertically
  - **Responsive Scrolling**: Both horizontal and vertical scrolling with proper header visibility

### Report Features
- **Responsive Design**: Works on desktop and mobile devices
- **Period Filtering**: Filter data by date range
- **Data Type Filtering**: Switch between Actual, Budget, and Forecast data
- **Export to Excel**: Download reports in Excel format
- **Print Functionality**: Print-friendly reports
- **Navigation Menu**: Easy switching between reports and other features
- **DataTables Integration**: Professional table library with fixed columns and scrolling
- **Fixed Columns**: Account Code and Account Name columns stay fixed on the left
- **Horizontal Scrolling**: Period columns scroll horizontally with smooth performance
- **Vertical Scrolling**: 500px height container with vertical scrolling
- **Compact Headers**: 11px font size prevents text wrapping in headers
- **Single-Line Account Names**: No text wrapping in Account Name column with ellipsis for long names
- **Consistent Font Sizes**: All table elements (Account Code, Account Name, numerical data) use 11px font size
- **Neutral Number Colors**: All positive numbers are black, negative numbers are red, zero values are gray
- **Professional Number Formatting**: Numbers display with thousand separators (1,000, 239,595) and right alignment
- **No Sorting**: Preserves exact database order from Chart of Accounts sort_order
- **Clean Interface**: No paging, search, or sorting controls for streamlined experience

## Project Structure

```
financial_consolidator/
├── core/                    # Main application
│   ├── models.py           # Database models
│   ├── admin.py            # Admin interface configuration
│   └── migrations/         # Database migrations
├── financial_consolidator/  # Project settings
│   ├── settings.py         # Django settings
│   ├── urls.py             # URL configuration
│   └── wsgi.py             # WSGI configuration
├── manage.py               # Django management script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Development

### Making Changes

1. **Update models**: Edit `core/models.py`
2. **Create migrations**: `python manage.py makemigrations`
3. **Apply migrations**: `python manage.py migrate`
4. **Update admin**: Edit `core/admin.py` if needed

### Testing

```bash
python manage.py test
```

## Troubleshooting

### PostgreSQL Connection Issues

- Ensure PostgreSQL is running
- Check database credentials in settings.py
- Verify database exists: `psql -U postgres -d consolidator_db`
- Check PostgreSQL logs for connection errors

### Migration Issues

- If migrations fail, try: `python manage.py migrate --fake-initial`
- Reset migrations: Delete migration files and run `makemigrations` again

## License

This project is for educational and development purposes.
