"""
This set of test cases ensures that the workflow is behaving itself.  

It tests that the mappings from workflow stages to plugins is working.  

It DOES NOT test the plugins themselves.  Any comments which say 
"check that we can identify a doi" or similar mean "check that the 
plugin and workflow framework support the identification of the doi".

All plugin work is done with mock functions defined below.

There are other tests for working on specific plugins.
"""

from unittest import TestCase
import config, workflow, models, cache, archive

CACHE = {}
ARCHIVE = []

def mock_cache(key, obj):
    global CACHE
    CACHE[key] = obj

def mock_store(bibjson):
    global ARCHIVE
    ARCHIVE.append(bibjson)

def mock_doi_type(bibjson_identifier):
    if bibjson_identifier["id"].startswith("10"):
        bibjson_identifier["type"] = "doi"
        return
    if bibjson_identifier.get("type") == "doi":
        raise models.LookupException("oi")

def mock_pmid_type(bibjson_identifier):
    if bibjson_identifier["id"] == "12345678":
        bibjson_identifier["type"] = "pmid"
        
def mock_doi_canon(bibjson_identifier):
    if bibjson_identifier['type'] == 'doi':
        bibjson_identifier['canonical'] = bibjson_identifier['type'] + ":" + bibjson_identifier['id']
    
def mock_pmid_canon(bibjson_identifier):
    if bibjson_identifier['type'] == 'pmid':
        bibjson_identifier['canonical'] = bibjson_identifier['type'] + ":" + bibjson_identifier['id']

def mock_check_cache(key):
    if key == "doi:10.none": return None
    if key == "doi:10.queued": return {"identifier" : {"id" : "10.queued", "type" : "doi", "canonical": "doi:10.queued"}, "queued" : True}
    if key == "doi:10.bibjson": return {"identifier" : {"id" : "10.bibjson", "type" : "doi", "canonical" : "doi:10.bibjson"}, "bibjson" : {"title" : "fresh"}}
    if key == "doi:10.stale": return {"identifier" : {"id" : "10.stale", "type" : "doi", "canonical" : "doi:10.stale"}, "bibjson" : {"title" : "stale"}}

def mock_queue_cache(key):
    return {"identifier" : {"id" : key}, "queued": True}

def mock_success_cache(key):
    return {"identifier" : {"id" : key}, "bibjson": {"title" : "cached"}}
    
def mock_null_cache(key): return None

def mock_check_archive(key):
    if key == "doi:10.none": return None
    if key == "doi:10.bibjson": return {"title" : "whatever"}
    if key == "doi:10.archived": return {"title" : "archived"}

def mock_null_archive(key): return None

def mock_detect_provider(record):
    record['provider'] = "http://provider"

def mock_no_provider(record): pass

def mock_other_detect(record):
    record['provider'] = "http://other"

def mock_licence_plugin(record):
    record['bibjson'] = {}
    record['bibjson']['license'] = {}
    record['bibjson']['title'] = "mytitle"

def mock_back_end(record): pass

def mock_is_stale(bibjson):
    return bibjson["title"] == "stale"
    
def mock_invalidate(key): pass

class TestWorkflow(TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass
        
    def test_01_detect_verify_type(self):
        config.type_detection = [mock_doi_type, mock_pmid_type]
        
        # check that we can identify a doi
        record = {"identifier" : {"id" : "10.blah"}}
        workflow._detect_verify_type(record)
        assert record["identifier"]["type"] == "doi"
        
        # check we can identify a pmid
        record = {"identifier" : {"id" : "12345678"}}
        workflow._detect_verify_type(record)
        assert record["identifier"]["type"] == "pmid"
        
        # check that we can deal with a lookup exception
        record = {"identifier" : {"id" : "123456789", "type" : "doi"}}
        with self.assertRaises(models.LookupException):
            workflow._detect_verify_type(record)
        
        # check that we can deal with an unidentifiable identifier
        record = {"identifier" : {"id" : "abcd"}}
        workflow._detect_verify_type(record)
        assert not record["identifier"].has_key("type")

    def test_02_canonicalise(self):
        config.canonicalisers = {"doi" : mock_doi_canon, "pmid" : mock_pmid_canon}
        
        # check that we can canonicalise a doi
        record = {"identifier" : {"id" : "10.123456789", "type" : "doi"}}
        workflow._canonicalise_identifier(record)
        assert record['identifier']['canonical'] == "doi:10.123456789"
        
        # check that we can canonicalise a pmid
        record = {"identifier" : {"id" : "12345678", "type" : "pmid"}}
        workflow._canonicalise_identifier(record)
        assert record['identifier']['canonical'] == "pmid:12345678", record['identifier']['canonical']
        
    def test_03_check_cache(self):
        cache.check_cache = mock_check_cache
        cache.is_stale = mock_is_stale
        cache.invalidate = mock_invalidate
        
        record = {"identifier" : {"id" : "10.none", "type" : "doi", "canonical" : "doi:10.none"}}
        cache_copy = workflow._check_cache(record)
        assert cache_copy is None
        
        record = {"identifier" : {"id" : "10.queued", "type" : "doi", "canonical" : "doi:10.queued"}}
        cache_copy = workflow._check_cache(record)
        assert cache_copy['queued']
        
        record = {"identifier" : {"id" : "10.bibjson", "type" : "doi", "canonical" : "doi:10.bibjson"}}
        cache_copy = workflow._check_cache(record)
        assert cache_copy.has_key("bibjson")
        assert cache_copy["bibjson"]["title"] == "fresh"
        
        record = {"identifier" : {"id" : "10.stale", "type" : "doi", "canonical" : "doi:10.stale"}}
        cache_copy = workflow._check_cache(record)
        assert cache_copy is None
        
    def test_04_check_archive(self):
        archive.check_archive = mock_check_archive
        
        record = {"identifier" : {"id" : "10.none", "type" : "doi", "canonical" : "doi:10.none"}}
        archive_copy = workflow._check_archive(record)
        assert archive_copy is None
        
        record = {"identifier" : {"id" : "10.bibjson", "type" : "doi", "canonical" : "doi:10.bibjson"}}
        archive_copy = workflow._check_archive(record)
        assert archive_copy.has_key("title")
    
    def test_05_cache_success(self):
        ids = [{"id" : "10.cached"}]
        
        # set up the mocks for the first test
        config.type_detection = [mock_doi_type, mock_pmid_type]
        config.canonicalisers = {"doi" : mock_doi_canon, "pmid" : mock_pmid_canon}
        cache.check_cache = mock_queue_cache
        
        # first do a lookup on a queued version
        rs = workflow.lookup(ids)
        assert len(rs.processing) == 1
        result = rs.processing[0]
        assert result['identifier']['id'] == "10.cached"
        assert result['identifier']['type'] == "doi"
        assert result['identifier']['canonical'] == "doi:10.cached"
        
        # now update the cache mock for the appropriate result
        cache.check_cache = mock_success_cache
        
        # now the same lookup on a properly cached version
        ids = [{"id" : "10.cached"}]
        rs = workflow.lookup(ids)
        assert len(rs.results) == 1
        result = rs.results[0]
        assert result['identifier'][0]['id'] == "10.cached"
        assert result['identifier'][0]['type'] == "doi"
        assert result['identifier'][0]['canonical'] == "doi:10.cached", result
        assert result['title'] == "cached"
    
    def test_06_archive_success(self):
        ids = [{"id" : "10.archived"}]
        
        # set up the mocks for the first test
        config.type_detection = [mock_doi_type, mock_pmid_type]
        config.canonicalisers = {"doi" : mock_doi_canon, "pmid" : mock_pmid_canon}
        cache.check_cache = mock_null_cache
        archive.check_archive = mock_check_archive
        
        # do a lookup for an archived version
        rs = workflow.lookup(ids)
        assert len(rs.results) == 1
        result = rs.results[0]
        assert result['identifier'][0]['id'] == "10.archived"
        assert result['identifier'][0]['type'] == "doi"
        assert result['identifier'][0]['canonical'] == "doi:10.archived", result
        assert result['title'] == "archived"
        
    def test_07_lookup_error(self):
        ids = [{"id" : "12345", "type" : "doi"}]
        config.type_detection = [mock_doi_type, mock_pmid_type]
        
        rs = workflow.lookup(ids)
        assert len(rs.errors) == 1
        result = rs.errors[0]
        assert result['identifier']['id'] == "12345"
        assert result['identifier']['type'] == "doi"
        assert result.has_key("error")
    
    def test_08_detect_provider(self):
        record = {"identifier" : {"id" : "12345"}}
        workflow.detect_provider(record)
        
        # the record should not have changed
        assert not record.has_key('provider')
        
        record['identifier']['type'] = "unknown"
        workflow.detect_provider(record)
        
        # the record should not have changed
        assert not record.has_key('provider')
        
        # check that a plugin is applied
        config.provider_detection = {"doi" : [mock_detect_provider]}
        record['identifier']['type'] = "doi"
        workflow.detect_provider(record)
        assert record.has_key("provider"), record
        assert record["provider"] == "http://provider"
        
        # now check that the chain exits after the first successful one
        config.provider_detection = {"doi" : [mock_no_provider, mock_other_detect, mock_detect_provider]}
        del record['provider']
        workflow.detect_provider(record)
        assert record.has_key("provider")
        assert record["provider"] == "http://other"
        
    def test_09_load_provider_plugin(self):
        # first try the simple case of a dictionary of plugins
        config.licence_detection = {"one" : "one", "two" : "two"}
        one = workflow._get_provider_plugin("one")
        two = workflow._get_provider_plugin("two")
        assert one == "one"
        assert two == "two"
        
        # now try a couple of granular ones
        config.licence_detection = {"one" : "one", "one/two" : "one/two", "two" : "two"}
        one = workflow._get_provider_plugin("one")
        onetwo = workflow._get_provider_plugin("one/two")
        otherone = workflow._get_provider_plugin("one/three")
        onetwothree = workflow._get_provider_plugin("one/two/three")
        assert one == "one"
        assert onetwo == "one/two"
        assert otherone == "one"
        assert onetwothree == "one/two"
    
    def test_10_provider_licence(self):
        config.licence_detection = {"testprovider" : mock_licence_plugin}
        
        # first check that no provider results in no change
        record = {}
        workflow.provider_licence(record)
        assert not record.has_key("bibjson")
        
        # now check there's no change if there's no plugin
        record['provider'] = "provider"
        workflow.provider_licence(record)
        assert not record.has_key("bibjson")
        
        # check that it works when it's right
        record['provider'] = "testprovider"
        workflow.provider_licence(record)
        assert record.has_key("bibjson")
        assert record['bibjson'].has_key("license") # american spelling
    
    def test_11_check_cache_update_on_queued(self):
        global CACHE
        ids = [{"id" : "10.queued"}]
        
        # set up the configuration so that the type and canonical form are created
        # but no copy of the id is found in the cache or archive
        config.type_detection = [mock_doi_type, mock_pmid_type]
        config.canonicalisers = {"doi" : mock_doi_canon, "pmid" : mock_pmid_canon}
        cache.check_cache = mock_null_cache
        archive.check_archive = mock_null_archive
        
        # mock out the cache method to allow us to record
        # calls to it
        cache.cache = mock_cache
        
        # mock out the _start_back_end so that we don't actually start the
        # back end
        old_back_end = workflow._start_back_end
        workflow._start_back_end = mock_back_end
        
        # do the lookup
        rs = workflow.lookup(ids)
        
        # assert that the result is in the appropriate bit of the response
        assert len(rs.processing) == 1
        result = rs.processing[0]
        assert result['identifier']['id'] == "10.queued"
        
        # now check our cache and make sure that the item got cached
        # correctly
        assert CACHE.has_key("doi:10.queued")
        assert CACHE["doi:10.queued"]['queued']
        
        
        # reset the test cache and reinstate the old back-end
        del CACHE["doi:10.queued"]
        workflow._start_back_end = old_back_end
    
    def test_12_store(self):
        global CACHE
        global ARCHIVE
        
        cache.cache = mock_cache
        archive.store = mock_store
        
        # first check that nothing happens if all the right fields aren't present
        record = {'identifier' : {"id" : "10.1", "type" : "doi", "canonical" : "doi:10.1"}, "queued" : True}
        workflow.store_results(record)
        assert not CACHE.has_key("doi:10.1")
        assert len(ARCHIVE) == 0
        
        record["bibjson"] = {"title" : "mytitle"}
        workflow.store_results(record)
        assert CACHE.has_key("doi:10.1")
        assert not CACHE["doi:10.1"].has_key("queued")
        assert len(ARCHIVE) == 1
        assert ARCHIVE[0]["title"] == "mytitle"
        
        del CACHE['doi:10.1']
        del ARCHIVE[0]
    
    def test_13_chain(self):
        global CACHE
        global ARCHIVE
        
        record = {'identifier' : {"id" : "10.1", "type" : "doi", "canonical" : "doi:10.1"}, "queued" : True}
        
        config.provider_detection = {"doi" : [mock_detect_provider]}
        config.licence_detection = {"http://prov" : mock_licence_plugin}
        
        # run the chain synchronously
        record = workflow.detect_provider(record)
        record = workflow.provider_licence(record)
        record = workflow.store_results(record)
        
        assert record.has_key("provider")
        assert record["provider"] == "http://provider"
        
        assert record.has_key("bibjson")
        assert record['bibjson'].has_key("license")
        
        assert CACHE.has_key("doi:10.1")
        assert not CACHE["doi:10.1"].has_key("queued")
        assert len(ARCHIVE) == 1
        assert ARCHIVE[0]["title"] == "mytitle"
        
        del CACHE['doi:10.1']
        del ARCHIVE[0]
        
        
        
        
        
        
        
        
        
        
        
        
        