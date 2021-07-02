import sqlite3

branchList = []
conn = sqlite3.connect('Branches.db')
def openDatabase():
    # Initialize a list and add all the branches from the database to said list   
    cursor = conn.execute("SELECT BRANCH from Branches WHERE BRANCH IS NOT NULL;")
    for branches in cursor:
        branches = str(branches).replace("(", "").replace(")","").replace("\'","")[:-1]
        branchList.append(branches)

    # Sorts the branch alphabetically
    branchList.sort()
