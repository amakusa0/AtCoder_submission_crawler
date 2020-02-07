import pandas as pd
import requests
import time
import sys
import re
import threading
from bs4 import BeautifulSoup
from language_encoder import language_encoder


class Crawler:
    def __init__(self, contest_id, submission_id, interval=5):
        self.contest_id = contest_id

        assert(interval>=1)
        self.interval = interval

        print('init_contest:<start>', end='')
        r = requests.get("https://atcoder.jp/contests/"+contest_id)
        print('<end>')
        self.prev_request_time = time.time()
        time.sleep(self.interval)
        soup = BeautifulSoup(r.text, "lxml")
        t_time = soup.find_all("time")
        self.end_date = t_time[1].text


        url = "https://atcoder.jp/contests/"+contest_id+"/submissions/"+submission_id

        print('init_submisssion:<start>', end='')
        r = requests.get(url)
        print("<end>:", round(time.time() - self.prev_request_time, 3))
        self.prev_request_time = time.time()
        time.sleep(self.interval)

        soup = BeautifulSoup(r.text, "lxml")

        self.wrong_pattern = []
        self.problem_alphabet=''
        language = ''
        self.judge_status = ''

        f = False
        for i,t in enumerate(soup.find_all("tr")):
            if i==1:
              self.problem_alphabet = t.find("a").text[0].lower()
            elif i==3:
                language = t.find("td", class_="text-center").text
                self.language_enc = language_encoder(language)
            elif i==6:
                self.judge_status = t.find("span").text
            elif i>6:
                if t.find("span", class_='label label-success')!=None or t.find("span", class_='label label-warning')!=None:
                    judge = t.find("span").text
                    self.wrong_pattern.append(int(judge=='AC'))

        assert(len(self.wrong_pattern)>0)
        assert('' not in [self.problem_alphabet, language, self.judge_status])

        print('='*40)
        print('url:', url)
        print('contest_id:', self.contest_id)
        print('problem_alphabet:', self.problem_alphabet)
        print('lanugage(encode):',language)
        print('judge_status:', self.judge_status)
        print('wrong_pattern:', self.wrong_pattern)
        print('='*40)

    def timekeeper(self, func, args=()):
        """
        (funcの実行時間が interval 秒より短い場合は) funcをinterval秒ごとに実行．
        """
        def wait_interval():
            """
            interval秒間，待つ．
            """
            time.sleep(self.interval)

        func_list = [wait_interval, func]
        args_list = [(), args]

        thread_list = []
        for func, args in zip(func_list, args_list):
            thread = threading.Thread(target=func, args=args)
            thread_list.append(thread)

        for thread in thread_list:
            thread.start()

        for thread in thread_list:
            thread.join()



    def get_num_page(self, url):
        """
        {AC, TLE, WA}一覧の１ページ目のurlを渡すと，
        全体のページ数を返す．
        """
        print("get_num_page:<start>", end='')
        r = requests.get(url)
        print('<end>:',   round(time.time() - self.prev_request_time, 3))
        self.prev_request_time = time.time()
        time.sleep(self.interval)

        soup = BeautifulSoup(r.text, "lxml")
        t = soup.find_all("ul", class_="pagination pagination-sm mt-0 mb-1")[0]
        t_a = t.find_all("a")
        return int(t_a[-1].text)



    def get_list(self, url, judge_status, based_user_id=False):
        """
        search_list関数で使う．timekeeper関数により，一定間隔で呼び出させる．　
        """
        global df

        print("%s_list, based_user_id %d:<start>"% (judge_status, based_user_id), end='')
        r = requests.get(url)
        print("<end>:", round(time.time() - self.prev_request_time, 3))
        self.prev_request_time = time.time()

        soup = BeautifulSoup(r.text, "lxml")

        for i,t in enumerate(soup.find_all("tr")):
            if i==0:
                continue
            t_a = t.find_all("a")
            t_time = t.find("time")
            if t_a[0].contents[0][0].lower()==self.problem_alphabet and t_time.text <= self.end_date:

                user_id = t_a[1].text
                url_detail = t_a[3].get("href")

                if judge_status!='AC': # WA or TLEの場合
                    df_temp = pd.Series( [user_id, judge_status, "https://atcoder.jp"+url_detail], index=df.columns )
                    df = df.append(df_temp, ignore_index=True )
                else: # AC の場合
                    if based_user_id or (user_id in df['user_id'].values):
                        df_temp = pd.Series( [user_id, "AC", "https://atcoder.jp"+url_detail], index=df.columns )
                        df = df.append(df_temp, ignore_index=True )
        return



    def search_list(self, isAC, based_user_id=False):
        """
        {AC, WA, TLE}の一覧からデータを取得し，dfに格納．
        isAC: boolean
        based_user_id: boolean，isAC=Trueの時のみ使う．
        """
        if isAC:
            status = "AC"
        else:
            status = self.judge_status

        url = "https://atcoder.jp/contests/"+self.contest_id\
        +"/submissions?f.Language="+str(self.language_enc)+"&f.Status="\
        +status+"&f.User=&page="

        num_page = self.get_num_page(url+'1')
        print(">> num_page_of_%s_list: %d"% (status, num_page))

        if isAC and based_user_id:
            global df
            for i,user_id in enumerate(set(df['user_id'])):
                # user_id を指定したURL．
                # 仮にその人の提出が2ページ以上あっても，1ページ目のみを取得．
                url_based_user_id = "https://atcoder.jp/contests/"+self.contest_id\
                +"/submissions?f.Language="+str(self.language_enc)+"&f.Status=AC"\
                "&f.User="+user_id+"&page=1"
                print('%4d :'%(i+1),end='')
                self.timekeeper(func=self.get_list, args=(url_based_user_id, 'AC', True, ))
        else:
            for i in range(1, num_page+1):
                print('%4d :'%i, end='')
                self.timekeeper(func=self.get_list, args=(url+str(i), status, False, ))



    def get_wrong_detail(self, idx):
        """
        search_wrong_detail関数で使う．timekeeper関数により，一定間隔で呼び出される．
        """
        global df

        print("%s_detail:<start>"%self.judge_status, end='')
        r = requests.get(df.loc[idx, 'url'])
        print("<end>:",  round(time.time() - self.prev_request_time, 3))
        self.prev_request_time = time.time()

        soup = BeautifulSoup(r.text, "lxml")

        temp_wrong_pattern = []

        for i, t in enumerate(soup.find_all("tr")):
            if  i>6 and (t.find("span", class_='label label-success')!=None or t.find("span", class_='label label-warning')!=None):
                judge = t.find("span").text
                temp_wrong_pattern.append(int(judge=='AC'))

        assert(len(temp_wrong_pattern)==len(self.wrong_pattern))

        if temp_wrong_pattern != self.wrong_pattern:
            df.drop(idx, inplace=True)



    def search_wrong_detail(self):
        """
        間違いパターンを判定.一致しない場合は，dfから削除．
        """
        global df

        print(">> num_detail: %d"% len(df))

        for i in df.index:
            print('%4d :'%(i+1),end='')
            self.timekeeper(func=self.get_wrong_detail, args=(i, ))



    def start(self):
        self.search_list(isAC=False)
        self.search_wrong_detail()

        url = "https://atcoder.jp/contests/"+self.contest_id\
        +"/submissions?f.Language="+str(self.language_enc)+"&f.Status=AC&f.User=&page=1"

        num_AC_page = self.get_num_page(url)
        num_user = len(set(df['user_id']))
        print('$$ num_AC_page:%d  vs  num_user:%d'%(num_AC_page, num_user))

        if(num_user<=0):
            return

        if num_AC_page < num_user:
            self.search_list(isAC=True, based_user_id=False)
        else:
            self.search_list(isAC=True, based_user_id=True)

        # 並び替え
        df['value_for_sort'] = 0
        AC_user_id = set(df[df['judge_status']=='AC']['user_id'])
        for user_id in AC_user_id:
            df['value_for_sort'].mask(df['user_id'] == user_id, -1, inplace=True)

        df['value_for_sort'] = df.apply(lambda x:(x[3], x[0], -1) if x[1]=='AC' else (x[3],x[0], 0), axis=1)
        df.sort_values('value_for_sort', inplace=True)
        df.drop('value_for_sort', axis=1, inplace=True)





df = pd.DataFrame({}, columns=['user_id', 'judge_status', 'url'])

def main():
    global df

    args = sys.argv
    if len(args)<3:
    	print('set contest_id and submission_id !')
    	print('>> main.py [contest_id] [submission_id]')
    	sys.exit()

    contest_id = args[1]
    submission_id = args[2]


    crawler = Crawler(
        contest_id= contest_id,
        submission_id = submission_id,
        interval=5
    )
    crawler.start()

    if isinstance(submission_id, int):
        submission_id = str(submission_id)
    df.to_csv("result_"+contest_id+"_"+str(submission_id)+".csv", index=False)
    print(df)


if __name__=='__main__':
    main()