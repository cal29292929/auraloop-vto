<!-- Reviewed by OpenAI Codex (gpt-6-luna) | Session ID: 01a17da5-425d-75c0-a350-505ae54a9d55 | Timestamp: 2026-10-27T22:56:54+09:00 -->

# Architecture & Security Review — `DESIGN_OPUS55.md`

**判定: 実装開始前に必須修正。**  
製品コンセプトとシミュレーション優先の方針はハッカソン向けですが、この文書の「Implementation-ready」という状態には達していません。YouCamのAPI契約、画像の受け渡し、障害時の状態遷移、MCPの仕様、プライバシー境界が未確定または矛盾しています。特に、外部API契約を推測のまま実装すると、ライブデモが成立しない可能性があります。

## 1. 重大な設計欠陥と実装リスク

### P0 — YouCam API契約が未検証

§4.1–4.3は、エンドポイント、認証方式、リクエスト本文、metric action名、応答形式、task polling、単位コストを「defaults」「as understood」としています。これは実装仕様ではありません。`skin-analysis`、`skin-tone-analysis`、`makeup-vto`、`cloth` のパスや、`actions` の構造、`file_sets` のフィールド名が実APIと一致する保証がありません。SD/HD action名と「14 metrics」の対応、スコアの向きが実際のAPI応答と一致するかも未確認です。

**影響:** 認証成功後にタスク作成が失敗する、metricが欠落する、結果を誤読する、不要なAPI unitsを消費する、といった障害が起こり得ます。「Day-1にPlaygroundで確認」はリスクを認識していますが、確認完了前にライブ統合を実装できる契約が文書にありません。

**必須対応:** APIごとに公式仕様またはPlaygroundで確認した契約を固定し、実リクエスト／応答 fixture を保存してください。確認できていないAPIを呼ぶ経路は、ライブ対応済みと扱わないでください。

### P0 — Chained VTOの入力・成果物契約が成立していない

Makeup結果をApparel VTOの入力にできるという前提が未検証です。結果URLが次のtaskで使える `file_id` なのか、ダウンロードして再アップロードできるのか、結果画像のURLに認証や有効期限があるのかが不明です。さらに、`garment_file_id` の取得・保存・アップロード手順が定義されていません。

`TryOnResult.image_ref` と `TryOnArtifact` の型・所有権・ライフサイクルも曖昧です。ライブの署名付きURL、ローカルの `sim://`、ブラウザ表示用URLが同じフィールドに入る設計では、UI・監査ログ・外部ツールへURLを漏らす危険があります。

**必須対応:** MakeupとApparelの各APIについて、source/ref画像の取得から結果表示までの実際のデータフローを定義してください。URL、file ID、画像バイト列を別型で扱い、presigned URLや一時的なAPI URLをレスポンス・ログ・監査イベントに含めないことを明記してください。Chained VTOがAPI上成立しない場合に備え、2つの結果を並べて表示する確実なfallbackを用意してください。

### P0 — 「task POSTは接続失敗時のみretry」の判定が実装不能

`urllib.request` でクライアントが接続エラーやtimeoutを受けても、サーバーが本文を受け取りtaskを作成したかを一般には判定できません。「server has received the body」の境界をクライアント側から確定できないため、仕様どおりの重複防止は保証できません。

**必須対応:** APIが提供するidempotency機構の有無を確認し、対応していれば安定したキーを使ってください。提供されない場合は、task作成POSTの結果が不明な失敗を `unknown_submission` として扱い、自動再送せず、明示的な回復経路へ遷移させてください。polling timeout、task error、キャンセル、単位消費の扱いも合わせて定義してください。

### P0 — セキュリティ・プライバシー境界の説明が不十分

「No images are stored anywhere」は設計からは保証できません。画像はYouCamへ送信され、ブラウザ、プロキシ、サーバーのメモリ、例外処理、アクセスログ、外部検索／LLM経路に残る可能性があります。YouCam側の保存・保持条件もこの設計にはありません。「Only scores are stored, on the user's device」についても、device側の保存先・消去条件・サーバーセッションとの関係が未定義です。

**必須対応:** データフロー表に、各データ（原画像、加工画像、結果画像、metric、製品選択、task ID、URL）の送信先、保持先、保持期間、削除条件を記載してください。外部APIへの送信前に、画像がYouCamへ送られることを含む明示的な同意を取得し、撤回・セッション終了時の挙動を実装してください。外部サービスの保持条件を確認できない場合、「保存されない」と断定しないでください。

### P1 — 入力検証が画像パーサー攻撃・過大処理を防がない

Magic-byte確認と8 MiB制限だけでは、壊れた画像、巨大な展開サイズ、極端な縦横比、複数フレーム、偽装MIME、画像処理負荷を防げません。EXIF除去の処理順序も不明で、EXIFを除去する実際のデコード／再エンコード処理が仕様化されていません。`ImageInput` がPNG/JPEGを許す一方、アップロード例はJPEG固定です。

**必須対応:** 信頼できる画像デコーダーで実際にデコードし、幅・高さ・総画素数・フレーム数・形式を制限してください。アップロードする形式とMIMEを正規化し、再エンコード後のデータだけを外部へ送ってください。処理時間・メモリ上限と不正入力時のAPIエラーも定義してください。

### P1 — Web APIの認証・ブラウザ防御が未設計

§6.2のHMAC認証は「retailer embed / webhook」向けとありますが、署名キーの配布・ローテーション・リプレイ防止・body canonicalizationが未定義です。Web Dashboardからの画像アップロードに誰がアクセスできるのか、セッションをどう分離するのかも記述がありません。`ThreadingHTTPServer` をインターネットに露出する場合、CORS、CSRF、Hostヘッダー、リクエスト本文上限、同時接続上限、TLS終端の前提が必要です。プロセス内rate limitは複数プロセスや再起動をまたいで効きません。

**必須対応:** デモ用のbind先をlocalhostに限定するか、外部公開する場合の認証・TLS・CORS・CSRF・リクエスト制限を決めてください。APIキーをブラウザへ渡さないこと、ユーザー／セッションごとの分離、rate-limit単位と失敗時の応答を明記してください。HMACは署名対象の正規化、タイムスタンプ許容範囲、nonceまたはリプレイ制御を含めて定義し、`X-Auralopp-Signature` のタイポも修正してください。

### P1 — SVG `data:` URIは画像出力・ブラウザ境界で危険かつ重い

シミュレーション画像を「SVG composite」とし、ユーザー画像を `data:` URI として埋め込む設計は、ブラウザのCSP・サニタイザー・サイズ上限との整合性がありません。生成SVGを未検証のまま表示すると、将来のテンプレート変更でスクリプトや外部参照を混入させる危険があります。`sim://look/<digest>` は通常のブラウザ画像URLとして利用できる仕様ではありません。

**必須対応:** シミュレーション成果物の表示方式（専用API、Blob URL等）を具体化し、SVGを返すなら安全な固定テンプレート、外部参照禁止、適切なCSP、サイズ制限を設けてください。画像を含むAPIレスポンスの最大サイズ、ブラウザでの表示・消去方法も定義してください。

### P1 — MCPはJSON-RPCだけでは完結しない

§8はMCP JSON-RPC 2.0 server と説明していますが、初期化、capabilities、tool discovery、tool schema、protocol version、通知、エラー応答、transportごとのフレーミングが設計にありません。HTTPで提供する場合の認証・セッション・Origin制限も未定義です。`server.py` が `/mcp` を提供し、`mcp_server.py` が `stdio | HTTP` を持つ構成は、HTTP実装の責任境界が重複しています。

**必須対応:** 対象MCP transportと対応プロトコル動作を確定し、実装するmethod、tool schema、JSON-RPC/MCP error mapping、画像を受け取る方法、consent確認方法を定義してください。MCP toolからも consent・budget・入力検証が迂回できないよう、すべての入口を同じengine境界に通してください。

### P1 — モード・fallbackの粒度がレスポンスモデルと矛盾

設計はproviderごとにlive/simulationを独立解決し、失敗した一工程だけsimulationへfallbackするとしています。しかし `ConciergeResult` に全体modeがなく、`SkinReport.mode` と `TryOnResult.mode` だけでは各工程の状態を表現できません。LLM・search・VTOの個別モード、fallback理由、部分成功がレスポンス契約にありません。ライブSkin AnalysisとシミュレーションVTOの結果をUIが「LIVE」と誤表示する可能性があります。

**必須対応:** 各工程のprovider、mode、fallback理由、成功／失敗状態を含む構造化 provenance を返してください。UIのLIVE表示は工程単位に限定し、ライブ結果と合成結果が混在したセッションに全体のLIVEバッジを出さないでください。fallbackで作ったデータをライブ成果として監査・Devpost動画に見せない仕組みも必要です。

### P1 — UnitBudgetは同時実行・並行要求で上限を超える

`reserve()` と `spent` の更新に同期、例外時の精算、task pollの消費、複数provider／複数request間の共有方法がありません。プロセス単位の既定50 unitsでは、複数worker・複数起動で制限が倍増します。また単位コストがplaceholderとされる一方、テストやライブ実行の上限が前提化されています。

**必須対応:** 予約・確定・取消の状態遷移を定義し、並行アクセスで原子的に上限を守ること。プロセス単位の上限でよいなら単一プロセス起動を強制し、そうでなければ共有ストアを使用してください。実コスト未確認時はライブ呼び出しを許可しない安全な設定にし、レスポンスに実際の消費／不明な消費を区別して記録してください。

### P1 — 医療的助言・LLM入力の安全境界が弱い

「cosmetic appearance scores」のdisclaimerはありますが、`acne < 30` や `redness < 25` を dermatology advisory に結びつける閾値の妥当性と、それ以外の重い症状・ユーザー記述への対応が定義されていません。retinoidの「avoid if pregnant / consult」は単純な文言で、健康上の判断を誤解させる可能性があります。LLMがTavily snippets、製品情報、ユーザー入力を受ける場合のprompt injection対策もありません。

**必須対応:** Regimenを診断・治療と誤認させない表示、医療相談を要するケースの保守的な文言、個別の健康判断をLLMに委ねない制約を定めてください。外部検索結果・製品データ・ユーザー入力はすべてuntrusted dataとして扱い、LLM出力は説明文など許可されたフィールドだけを採用してください。引用元URLの検証と、根拠のない効能表現を表示しないルールも追加してください。

## 2. データモデル・計算仕様の問題

- `@dataclass(frozen=True)` は入れ子の `dict` / `list` を不変にしません。`LookSpec.makeup`、`garment`、`ConciergeResult.metrics`、LLM schemaなどはmutableです。canonical serializationの安定性とhashableという主張に反します。immutableな専用型または正規化済みJSON値に置き換えてください。
- `SkinReport.tone` は必須ですが、§4.2はskin-tone分析をoptionalとしています。tone API失敗時にLab推定する条件、信頼度、provider provenanceを定義してください。tone推定失敗で全フローが失敗するのかも明記が必要です。
- `SkinReport.metrics` は「exactly 14」と「ordered as METRICS」の両方を保証する必要があります。表のmetric名・YouCam action・スコア方向をparserの契約として検証し、欠落・未知action・重複・null・範囲外値の扱いを定義してください。欠損値を健康スコアへ暗黙に含めないでください。
- `raw` の意味とスコア変換式が不明です。YouCam値が高いほど悪いmetricをどう反転し、`raw` に何を保存するのかを固定してください。API応答をfixtureで検証するまでは、この変換に依存するregimenや表示を有効にしないこと。
- `SkinTone.lab` はD65とありますが、YouCamが返す色空間、white point、hex変換、色域外値処理が未定義です。Fitzpatrick tableは肌色を代表する単一の測定尺度ではないため、シミュレーション専用と明示し、実測値と混同しないようにしてください。
- ΔE2000・sRGB→XYZ→Lab・undertone・apparel harmonyをpure Pythonで実装するなら、参照値fixture、境界値、既知の色差ペアでの決定的テストが必要です。式の定数・white point・ガンマ変換・浮動小数点許容誤差も仕様化してください。
- `Severity` のしきい値と「Trigger severity ≥」の意味が数値ルールと接続されていません。各metricで「低スコアほど懸念が強い」のかを固定してください。`oiliness` と `pores` の表記は、スコア方向に合わせた条件式と確認が必要です。
- `Concern Priority` の上位3件を選ぶ際の同点処理、confidenceが低い場合、user goalとの競合、重み合計が1でない場合を定義してください。
- `CartBuilder` の「Greedy knapsack by priority/price」は一般にknapsackの最適解を保証せず、価格0の場合の除算も未定義です。複数通貨、budget未指定、予算未満の同点、空カート、在庫切れ、同一SKU重複を含めた確定的な選択規則を定義してください。
- `Product.currency` と `Cart.currency` の一致、`checkout_url` の許可ホスト、数量の正整数制約がありません。外部URLを無制限に受け入れる設計はopen redirectの入口になります。
- すべての `str` に対する512文字制限だけでは、HTML、URL、制御文字、Unicode正規化、理由文の表示時XSSを防げません。出力をHTMLとして安全にエスケープし、URLは許可方式・hostで検証してください。
- `AuditEvent.ts` の時刻形式、イベント順序、並行sessionの分離が未定義です。HMAC digestがephemeral key依存なら、プロセス再起動後に監査検証できません。hash chainは単独では改ざん耐性を保証せず、末尾hashを別途保護しない限り全体を書き換えられます。セッション中の整合性確認と、長期の改ざん検知を区別してください。
- §7.4は「Audit trails live only in」で文書が途切れています。保存先、保持期間、アクセス制御、例外時の破棄方針が欠落しています。

## 3. ハッカソン要件・賞・提出物のレビュー

### Hackathon要件カバレッジ

Skin AIとeCommerce VTOを組み合わせる案はテーマに合います。ただし、設計が示すのは主に内部シミュレーションです。**ライブYouCam統合の確証、実際のVTO成果、動作する購入導線**はまだ証明されていません。「APIを3つchainする」こと自体が価値ではなく、実API上で成立し、ユーザーが確認できる結果であることを示す必要があります。

また、実際の製品カタログ、SKU、価格、在庫、ブランド許諾、checkoutの実行先がありません。`checkout_url` がmock/sandboxでも、現状の設計では誰がそのURLを作り、どのような購入体験を示すかが未定義です。Impactの根拠として挙げる「returns」「retailer value」も、計測方法や実データがありません。デモで主張する価値は、実装で観測できる範囲に合わせてください。

### Prize optimization

- 主賞を狙うなら、ライブAPIの動作確認と見せる価値を優先してください。MCP、Nebius、Tavily、長期metric loop、独自HTTP APIを同時に完成させる計画は、短い実装期間に対して過大です。
- 「MCP」「agentic」「AI」自体は審査優位性を保証しません。各要素がユーザー課題をどう解決するか、実装済みのデモ証拠で示す必要があります。
- Share & Earnの記述は、投稿条件・締切・対象となる投稿が確認済みの仕様ではありません。ボーナスunitsの配分に含める前に公式条件を確認してください。
- 「Women in Tech」「Rising Star」を狙わない判断は設計上の選択として問題ありませんが、資格要件・チーム情報を仕様側から推定していない点は維持してください。

### Devpost提出物の不足・期限リスク

§2.3のチェックリストは有用ですが、提出完了条件を満たす工程がスケジュールにありません。公開repo、MIT `LICENSE`、`README.md`、スクリーンショット、1–3分の公開YouTube動画、Devpostの説明文を誰がいつ作り、レビューするかが不明です。YouCam API名を動画で正確に表示する条件や、動画で使う成果がliveかsimulationかを明示する条件も実行可能な手順になっていません。

期限について、文書は「internal code-freeze」と「official cutoff」を別に置いていますが、提出フォームの実際の締切、timezone表示、動画の公開・リンク反映、repo公開の確認を含む提出完了バッファが定義されていません。公式ページで締切と提出要件を再確認し、提出作業をコード凍結後の余り時間に依存させないでください。文書の終端が欠けているため、後半の実装・提出計画が存在するかも確認不能です。

## 4. 障害処理・運用仕様の不足

- 1リクエストあたり60秒のdeadlineは、複数taskを直列実行する全フローの上限とは限りません。Concierge全体のdeadline、各providerへの残時間配分、ユーザー切断時のキャンセルを定義してください。
- HTTP 200でも、YouCam応答内の `status` が失敗するケースがあります。HTTP statusとAPI業務statusの両方を検証し、未知のtask状態・不正JSON・空results・部分resultsを処理してください。
- `Retry-After` のHTTP-date解釈、負値・不正値、壁時計の変化、overall deadline超過時の挙動を定義してください。テスト時は時計・乱数・transportをすべて注入し、実sleepなしで再現可能にしてください。
- 429時に同時要求が一斉再送される可能性があります。retry budget、同時実行上限、backoff上限、providerごとのcircuit breakerの要否を決めてください。
- 1工程のfallback後に次工程へ進める条件がありません。たとえばSkin Analysis失敗時に、シミュレーションmetricをライブ結果と同じカート判断へ使うのかを決めてください。
- fallbackも失敗した場合、部分結果を返すのか全体を中止するのかが未定義です。APIのHTTP status、ユーザー向けエラー、再試行可否、監査イベントをエラーコードごとに定義してください。
- ログで「path template」のみ記録する方針は適切ですが、エラーメッセージや例外文字列にURL・header・bodyが含まれない保証が必要です。例外のredactionをテストしてください。

## 5. 必須の決定的テスト要件

「約120 unit tests」「recorded live-response fixtures」という予定数は品質保証になりません。次の契約を再現可能に検証するテストを、実装受け入れ条件として指定してください。

- YouCamの各APIについて、保存済みfixtureからrequest serialization、response parsing、metric mapping、状態遷移を検証する。秘密情報・実ユーザー画像・署名付きURLをfixtureへ含めない。
- API応答の欠落項目、型違い、未知状態、API-level error、429、5xx、timeout、接続切断、polling deadlineを検証する。
- task POSTが結果不明になった場合に自動で二重送信しないことを検証する。
- `UnitBudget` の境界、並行予約、失敗・取消・不明な消費、複数工程の合計を検証する。
- simulation modeでsocket/networkアクセスがゼロであること、固定seedで全出力が同一であること、実時間sleepがないことを検証する。画像を異にした場合のfixtureも固定する。
- Skin metricの14項目、範囲、方向変換、confidence、欠損・重複・未知項目を検証する。
- CIEDE2000の既知ペア、sRGB変換、undertone境界、NaN/Inf、色域外入力を検証する。
- Cartの予算境界、通貨不一致、ゼロ価格、同点、重複SKU、空カタログ、在庫切れを検証する。
- HMACの有効署名、改ざん、期限切れ、リプレイ、キー欠落、定数時間比較の呼び出し境界を検証する。
- 画像の偽装MIME、壊れたファイル、画素数過大、縦横比過大、サイズ上限、EXIF除去を検証する。
- Web/MCP双方でconsent必須、provider経路共通、入力上限、エラー応答、画像や秘密情報がログに出ないことを検証する。
- 監査chainの改ざん検出、順序、セッション分離、ephemeral key変更後の期待動作を検証する。

## Mandatory Fixes for Implementation (Sakura `preview/Kimi-K2.7-Code`)

- [ ] **実装対象を凍結する:** 必須デモ経路を「画像入力 → YouCam Skin Analysis → 決定的な商品／routine選択 → YouCam VTO → 結果表示」に絞り、MCP、LLM、Tavily、長期追跡は追加要件として扱う。主賞の評価に直結するライブ成果を先に成立させる。
- [ ] **YouCam契約を実証してから固定する:** 各endpoint、auth、upload headers、task payload、metric action、result schema、単位コスト、task状態を公式仕様／Playgroundで確認し、redacted fixturesとschema validationを作る。未確認のpathやpayloadを推測でライブ送信しない。
- [ ] **全工程のprovenanceを返す:** skin、tone、makeup、apparel、LLM、searchごとに `provider`、`mode`、`status`、`degraded_reason`、`units` を記録し、混在結果を全体LIVEと表示しない。
- [ ] **task再送を安全化する:** APIのidempotency機構を調査する。ない場合、POST結果不明時は自動再送しない。polling timeout、terminal error、キャンセル、部分成功の回復状態を定義する。
- [ ] **画像処理の安全境界を実装する:** デコード検証、画素数・縦横比・フレーム制限、形式正規化、再エンコード、EXIF除去を行う。外部送信前の同意、画像の保持・削除、API事業者への送信説明をUIと仕様に反映する。
- [ ] **Web APIを安全に公開する:** localhost限定か外部公開かを決め、認証、TLS、CORS、CSRF、body上限、同時接続数、セッション分離、rate limitを実装する。ブラウザにprovider keyを渡さない。
- [ ] **成果画像の型と配信方法を分離する:** `sim://`、YouCam結果URL、file ID、画像bytesを同一の `image_ref` に混在させない。presigned URLをログ・レスポンス・監査に漏らさず、Chained VTO不成立時の表示fallbackを用意する。
- [ ] **MCPの責任範囲を確定する:** 対象transport、protocol version、初期化、tool schema、error mapping、HTTP認証・Origin制限を決定する。MCPからも同じconsent・budget・validation境界を必ず通す。
- [ ] **データモデルの不変性とschemaを直す:** mutableな `dict` / `list` を専用immutable型へ置き換える。optional tone、欠損metric、数値方向、通貨、checkout URL、数量、文字列出力を明示的に検証する。
- [ ] **予算・カートを決定的にする:** unit予約の並行安全性と不明消費を扱う。実API costが未確認ならliveを拒否する。Cartは通貨一致、ゼロ価格、同点、空カート、在庫、checkout hostを含めた明示的規則で作る。
- [ ] **医療・LLMガードレールを強化する:** 表示文を美容上の参考情報に限定し、LLMに診断・安全判断・価格・metric変換をさせない。検索結果やユーザー入力をuntrustedとして扱い、許可フィールド以外を破棄する。
- [ ] **決定的な契約テストを受け入れ条件にする:** 上記「必須の決定的テスト要件」を実装順にテスト化する。simulationはnetworkゼロ・実sleepゼロ・固定seedで再現でき、live parserは保存fixtureだけでCI検証できること。
- [ ] **提出物をスケジュール上の成果物にする:** 公開repo、MIT `LICENSE`、起動手順付きREADME、screenshots、1–3分の公開動画、Devpost説明文を担当・期限付きで計画する。動画でAPI名とLIVE/SIMULATEDの区別を正確に示し、締切・timezone・提出完了条件を公式情報で再確認する。
- [ ] **文書を完成させる:** §7.4の途中で切れている本文を復元し、監査ログの保存先・保持期間・削除方針、および残りの実装・提出設計を記載してから「implementation-ready」と評価する。
