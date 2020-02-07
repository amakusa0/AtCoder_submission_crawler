# AtCoder submission crawler

同じパターンの間違いと，そのユーザによる正解解答のリンクを集める．同じ言語で，コンテスト時間内の解答に限定する．


### 実行方法
```
python main.py [コンテスト名] [提出番号]
```

以下の解答と同じパターンの間違いと，そのユーザによる正解を集める場合<br>
[https://atcoder.jp/contests/abc152/submissions/9612781](https://atcoder.jp/contests/abc152/submissions/9612781)
```
python main.py abc152 9612781
```

公式の解説では，最小公倍数を素因数分解する方法が説明されていたが，少し工夫をすることで，Pythonでは素因数分解をしなくても正解できるようでした．
