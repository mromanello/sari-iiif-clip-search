import csv
import urllib.request
from hashlib import blake2b
from pathlib import Path
from SPARQLWrapper import SPARQLWrapper, JSON
from multiprocessing.pool import ThreadPool

class Images:
    
    MODE_SPARQL = 1
    MODE_CSV = 2

    def __init__(self, *, 
        mode=MODE_CSV, 
        endpoint=None, 
        iiifColumn="iiif_url",
        imageCSV,
        imageDir, 
        imageQuery=None, 
        threads=16):
        if not imageDir:
            raise Exception("imageDir is required")
        if not imageCSV:
            raise Exception("imageCSV is required in all modes")
        if mode == self.MODE_SPARQL:
            if not imageQuery:
                raise Exception("imageQuery is required in SPARQL mode")
            if not endpoint:
                raise Exception("endpoint is required in SPARQL mode")

        self.mode = mode
        self.iiifColumn = iiifColumn
        self.imageDir = imageDir
        self.imageCSV = imageCSV
        self.threads = threads
        
        if self.mode == self.MODE_SPARQL:
            self.imageQuery = imageQuery
            self.endpoint = endpoint

    def _customHash(self, inputString):
        h = blake2b(digest_size=20)
        h.update(inputString.encode())
        return h.hexdigest()

    def _downloadImage(self, iiifUrl):
        width = 640
        url = iiifUrl + '/full/' + str(width) + ',/0/default.jpg'
        photoId = self._customHash(iiifUrl)
        photoPath = Path(self.imageDir) / (photoId + ".jpg")

        # Only download a photo if it doesn't exist
        if not photoPath.exists():
            try:
                urllib.request.urlretrieve(url, photoPath)
            except:
                # Catch the exception if the download fails for some reason
                print(f"Cannot download {url}")
                pass

    def _saveSPARQLResultToCSV(self, sparqlResult):
        # Save to CSV
        fieldnames = sparqlResult['head']['vars']
        with open(self.imageCSV, 'w') as f:
            csvWriter = csv.DictWriter(f, fieldnames=fieldnames)
            csvWriter.writeheader()
            for result in sparqlResult['results']['bindings']:
                row = {}
                for field in fieldnames:
                    row[field] = result[field]['value']
                csvWriter.writerow(row)

    def downloadImages(self):
        urls = []
        with open(self.imageCSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urls.append(row[self.iiifColumn])

        pool = ThreadPool(self.threads)
        pool.map(self._downloadImage, urls)

    def queryImages(self):
        # Execute Query
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(self.imageQuery)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
        except Exception as e:
            return e
        # Save to CSV
        try:
            self._saveSPARQLResultToCSV(results)
        except Exception as e:
            return e

        return True
        