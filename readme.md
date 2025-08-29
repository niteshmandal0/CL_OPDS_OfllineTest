python3 opds.py --crawl-resources --base-out-url https://curious-reader.web.app --crawl-timeout-ms 30000 --verbose


python download_and_rewrite.py --manifest updated.json --out-root ./local_www --concurrency 8 --serve

python download_and_rewrite.py --manifest /home/nitesh-kumar/Documents/GitHub/curious-learning-assests/opds/curious-reader/public/lessons/cr_lang/ftm_af_1.json --out-root ./local_www --concurrency 8 --serve



/home/nitesh-kumar/Documents/GitHub/curious-learning-assests/opds/curious-reader/public/lessons/cr_lang/ftm_en_1.json


python3 download_from_har.py curiousreader-respect-ftm.web.app.har

python3 update_resources_from_har.py ftm_en_1.json curiousreader-respect-ftm.web.app.har updated.json


python extract_har_urls.py curiousreader-respect-ftm.web.app.har output.json

