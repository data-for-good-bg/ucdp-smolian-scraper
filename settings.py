import os

# -------- SETTINGS DEFINED BY USER
crawl_all = False  # do we want to craw all pages (~76) if FALSE - only the most recent archive

# input selected files in case you want some specific files to be downloaded
# (if those already exists, they will not be downloaded -> todo: rewrite to overwrite them
selected_files = ['https://auction.ucdp-smolian.com/publicInfo?printid=2321994d85d661d792223f647000c65f'
    , 'https://auction.ucdp-smolian.com/publicInfo?printid=059fdcd96baeb75112f09fa1dcc740cc'
    , 'https://auction.ucdp-smolian.com/publicInfo?printid=bdc4626aa1d1df8e14d80d345b2a442d'
                  ]

# additional settings
MAIN_PATH = os.getcwd()
path = 'exports/archive'
