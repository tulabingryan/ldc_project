import os
import time

'''
Note: In order for the git command to be automated
credentials should be stored first using the following command
git config credential.helper store
followed by git pull, which will ask for the credentials, which will be stored...
The next git commands will no longer ask for the credentials
'''

def main():
	while True:
		try:
			os.system('git pull')  # pull latest updates
			print('Files updated... sleeping for 1 hour...')
			os.system('git gc --aggressive --prune=now')  # reduce '.git' folder size
			time.sleep(3600)
		except KeyboardInterrupt:
			break
		except Exception as e:
			print(f"Error git_auto.py{e}")

if __name__ == '__main__':
	main()