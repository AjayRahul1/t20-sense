# T20 Sense

> Data Analytics in the Cricket World and even more...

| Field of Cricket Analysis has lot of empty shoes to fill. Don't you think? |
|:--:|

- Ever wanted to get inside of Cricketing World?
- A world full of detailing, analyzing, predicting and even more needs some attention to put.
- Cricket statistics play a major role in understanding what happened previously and how it can create a way for what's going to happen in the present.
- It can be something like performance of a previous player deciding his execution in coming matches that decides the performance and result of a team.
- Don't be late anymore. Now a lot of statistics about cricket are at your fingertips. Swim & Deep dive this world!

## Steps to Clone, Install, `Run` the project

### Cloning the project locally

For HTTPS Method,

```sh
# Cloning the GitHub Repository
git clone https://github.com/AjayRahul1/t20-sense.git

# Going into the directory
cd t20-sense/
```

For SSH Method (Prefer this only if SSH Key was setup on your computer),

```sh
# Cloning the GitHub Repository
git clone git@github.com:AjayRahul1/t20-sense.git

# Going into the directory
cd t20-sense/
```

### For Windows

#### Create a virtual environment with Python 3.12.x version

- This works with 3.11 and 3.10 too. Skip to [Creation of Virtual Environment](#creation-of-virtual-environment) step if you already have one of the py version installed

##### Python Version 3.12 Installation

- Go to [Python Official Downloads](https://www.python.org/downloads/) Page
- Download 3.12.x version (x can be any number you find there)
- Run the installer file.
- Check tick the `Add Python to PATH`.
- During installation, make sure to select the option `Customize installation`.
- Choose a unique installation directory for Python 3.12.x to avoid overwriting your existing Python version 3.x.x installation.
- If 'Add Python to Path' is `not` checked, open PATH Environment Variables and edit PATH variable by adding Python 3.12 version.

- Verify Python Version
  - ```python --version```

##### Creation of Virtual Environment

- ```python -m venv venv```
- Activating Virtual Environment
  - In Windows 10, Open Powershell (or) In Windows 11, Windows Terminal. 
  - ```venv\Scripts\Activate```
  - If you face any `error` with this command, it's because Microsoft disables Running Scripts by default.
  - To enable it temporarily, we run following command and try above command again.
    - ```powershell -ExecutionPolicy bypass```

##### Installing Requirements

- Check whether you can see (venv) in the terminal that gives the sign of successful virtual environment activation
- ```pip install -r requirements.txt```
- Take a moment of rest and comeback later while the requirements gets installed.

##### Set Environment Variables

- This is an optional step that improves performance.
- If you have a Google Cloud Platform Key, you have to set two Environment Variables.
- `setx API_KEY="your_gcp_key_name.json"`
- `setx BUCKET_NAME="gcp_bucket_name"`
- run setup_bucket_functions.py with your key to set up required files onto your `Google Cloud Storage` Buckets.
  - This takes 30 mins to 1 hour of time to setup all the required files.

##### Run the project on LocalHost

- ```uvicorn main:app --reload```
- Open [LocalHost](http://127.0.0.1:8000/) on your computer
- `Optional`: You can change the port number as per your wish.
- Now so many statistics about cricket are at your feet. Deep dive this world!

### For Linux (CLI Commands)

- First go to the folder where you want to clone using `cd your-directory-path/`
- Then copy below commands in your terminal in Linux. All done.

Ubuntu

```sh
# Verifying Python v3.11
python3 --version
# Create Virtual Environment with name 'venv'
python3 -m venv venv
# Activating Virtual Environment
source venv/bin/activate
# Installing Requirements
pip install -r requirements.txt
# setting up environment variables of Google Cloud Platform
export API_KEY="your_gcp_key_name.json"
export BUCKET_NAME="gcp_bucket_name"
# Run the project on LocalHost
uvicorn main:app --reload
```

Fedora

```sh
# Verifying Python v3.11
python --version
# Create Virtual Environment with name 'venv'
python -m venv venv
# Activating Virtual Environment
source venv/bin/activate
# Installing Requirements
pip install -r requirements.txt
# setting up environment variables of Google Cloud Platform
export API_KEY="your_gcp_key_name.json"
export BUCKET_NAME="gcp_bucket_name"
# Run the project on LocalHost
uvicorn main:app --reload
```

## ♥ Developed by

- Ajay Rahul • [![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=plastic&logo=github&logoColor=white)](https://github.com/AjayRahul1/)
- Sandeep Kondeti • [![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=plastic&logo=github&logoColor=white)](https://github.com/sandeep-006)
- Pranay Reddy • [![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=plastic&logo=github&logoColor=white)](https://github.com/pranayreddy241)
