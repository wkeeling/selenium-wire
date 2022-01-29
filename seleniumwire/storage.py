import logging
import os
import pickle
import re
import shutil
import sys
import tempfile
import threading
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import DefaultDict, Iterator, List, Optional, Union

from seleniumwire.request import Request, Response, WebSocketMessage

log = logging.getLogger(__name__)

# Storage folders older than this are cleaned up.
REMOVE_DATA_OLDER_THAN_DAYS = 1


def create(*, memory_only: bool = False, **kwargs):
    """Create a new storage instance.

    Args:
        memory_only: When True, an in-memory implementation will be used which stores
            request data in memory only and nothing on disk. Default False.
        kwargs: Any arguments to initialise the storage with:
            - base_dir: The base directory under which requests are stored
            - maxsize: The maximum number of requests the storage can hold
    Returns: A request storage implementation, currently either RequestStorage (default)
        or InMemoryRequestStorage when memory_only is set to True.
    """
    if memory_only:
        log.info('Using in-memory request storage')
        return InMemoryRequestStorage(base_dir=kwargs.get('base_dir'), maxsize=kwargs.get('maxsize'))

    log.info('Using default request storage')
    return RequestStorage(base_dir=kwargs.get('base_dir'))


class _IndexedRequest:
    def __init__(self, id: str, url: str, has_response: bool):
        self.id = id
        self.url = url
        self.has_response = has_response


class RequestStorage:
    """Responsible for persistence of request and response data to disk.

    This implementation writes the request and response data to disk, but keeps an in-memory
    index for sequencing and fast retrieval.

    Instances are designed to be threadsafe.
    """

    def __init__(self, base_dir: Optional[str] = None):
        """Initialises a new RequestStorage using an optional base directory.

        Args:
            base_dir: The directory where request and response data is stored.
                If not specified, the system temp folder is used.
        """
        if base_dir is None:
            base_dir = tempfile.gettempdir()

        self.home_dir: str = os.path.join(base_dir, '.seleniumwire')
        self.session_dir: str = os.path.join(self.home_dir, 'storage-{}'.format(str(uuid.uuid4())))
        os.makedirs(self.session_dir, exist_ok=True)
        self._cleanup_old_dirs()

        # Index of requests received.
        self._index: List[_IndexedRequest] = []

        # Sequences of websocket messages held against the
        # id of the originating websocket request.
        self._ws_messages: DefaultDict[str, List] = defaultdict(list)

        self._lock = threading.Lock()

    def save_request(self, request: Request) -> None:
        """Save a request to storage.

        Args:
            request: The request to save.
        """
        request_id = str(uuid.uuid4())
        request_dir = self._get_request_dir(request_id)
        os.mkdir(request_dir)
        request.id = request_id

        self._save(request, request_dir, 'request')

        with self._lock:
            self._index.append(_IndexedRequest(id=request_id, url=request.url, has_response=False))

    def _save(self, obj: Union[Request, Response, dict], dirname: str, filename: str) -> None:
        with open(os.path.join(dirname, filename), 'wb') as out:
            pickle.dump(obj, out)

    def save_response(self, request_id: str, response: Response) -> None:
        """Save a response to storage against a request with the specified id.

        Args:
            request_id: The id of the original request.
            response: The response to save.
        """
        indexed_request = self._get_indexed_request(request_id)

        if indexed_request is None:
            log.debug('Cannot save response as request %s is no longer stored', request_id)
            return

        request_dir = self._get_request_dir(request_id)

        self._save(response, request_dir, 'response')

        indexed_request.has_response = True

    def _get_indexed_request(self, request_id: str) -> Optional[_IndexedRequest]:
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            if indexed_request.id == request_id:
                return indexed_request

        return None

    def save_ws_message(self, request_id: str, message: WebSocketMessage) -> None:
        """Save a websocket message against a request with the specified id.

        Args:
            request_id: The id of the original handshake request.
            message: The websocket message to save.
        """
        with self._lock:
            self._ws_messages[request_id].append(message)

    def save_har_entry(self, request_id: str, entry: dict) -> None:
        """Save a HAR entry to storage against a request with the specified id.

        Args:
            request_id: The id of the original request.
            entry: The HAR entry to save.
        """
        indexed_request = self._get_indexed_request(request_id)

        if indexed_request is None:
            log.debug('Cannot save HAR entry as request %s is no longer stored', request_id)
            return

        request_dir = self._get_request_dir(request_id)

        self._save(entry, request_dir, 'har_entry')

    def load_requests(self) -> List[Request]:
        """Load all previously saved requests known to the storage (known to its index).

        The requests are returned as a list of request objects in the order in which they
        were saved. Each request will have any associated response and websocket messages
        attached if they exist.

        Returns: A list of request objects.
        """
        with self._lock:
            index = self._index[:]

        loaded = []

        for indexed_request in index:
            request = self._load_request(indexed_request.id)

            if request is not None:
                loaded.append(request)

        return loaded

    def _load_request(self, request_id: str) -> Optional[Request]:
        request_dir = self._get_request_dir(request_id)

        with open(os.path.join(request_dir, 'request'), 'rb') as req:
            request = self._unpickle(req)

            if request is None:
                return None

            ws_messages = self._ws_messages.get(request.id)

            if ws_messages:
                # Attach any websocket messages for this request if we have them
                request.ws_messages = ws_messages

            try:
                # Attach the response if there is one.
                with open(os.path.join(request_dir, 'response'), 'rb') as res:
                    response = self._unpickle(res)

                    if response is not None:
                        request.response = response

                        # The certificate data has been stored on the response but we make
                        # it available on the request which is a more logical location.
                        if hasattr(response, 'cert'):
                            request.cert = response.cert
                            del response.cert
            except (FileNotFoundError, EOFError):
                pass

        return request

    def _unpickle(self, f):
        """Unpickle the object specified by the file f.

        If unpickling fails return None.
        """
        try:
            return pickle.load(f)
        except Exception:
            # Errors may sometimes occur with unpickling - e.g.
            # sometimes data hasn't been fully flushed to disk
            # by the OS by the time we come to unpickle it.
            if log.isEnabledFor(logging.DEBUG):
                log.exception('Error unpickling object')

            return None

    def load_last_request(self) -> Optional[Request]:
        """Load the last saved request.

        Returns: The last saved request or None if no requests have
            yet been stored.
        """
        with self._lock:
            if self._index:
                last_request = self._index[-1]
            else:
                return None

        return self._load_request(last_request.id)

    def load_har_entries(self) -> List[dict]:
        """Load all HAR entries known to this storage.

        Returns: A list of HAR entries.
        """
        with self._lock:
            index = self._index[:]

        entries = []

        for indexed_request in index:
            request_dir = self._get_request_dir(indexed_request.id)

            try:
                with open(os.path.join(request_dir, 'har_entry'), 'rb') as f:
                    entry = self._unpickle(f)

                    if entry is not None:
                        entries.append(entry)
            except FileNotFoundError:
                # HAR entries aren't necessarily saved with each request.
                pass

        return entries

    def iter_requests(self) -> Iterator[Request]:
        """Return an iterator of requests known to the storage.

        Returns: An iterator of request objects.
        """
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            yield self._load_request(indexed_request.id)

    def clear_requests(self) -> None:
        """Clear all requests currently known to this storage."""
        with self._lock:
            index = self._index[:]
            self._index.clear()
            self._ws_messages.clear()

        for indexed_request in index:
            shutil.rmtree(self._get_request_dir(indexed_request.id), ignore_errors=True)

    def find(self, pat: str, check_response: bool = True) -> Optional[Request]:
        """Find the first request that matches the specified pattern.

        Requests are searched in chronological order.

        Args:
            pat: A pattern that will be searched in the request URL.
            check_response: When a match is found, whether to check that the request has
                a corresponding response. Where check_response=True and no response has
                been received, this method will skip the request and continue searching.

        Returns: The first request in the storage that matches the pattern,
            or None if no requests match.
        """
        with self._lock:
            index = self._index[:]

        for indexed_request in index:
            if re.search(pat, indexed_request.url):
                if (check_response and indexed_request.has_response) or not check_response:
                    return self._load_request(indexed_request.id)

        return None

    def _get_request_dir(self, request_id: str) -> str:
        return os.path.join(self.session_dir, 'request-{}'.format(request_id))

    def cleanup(self) -> None:
        """Remove all stored requests, the storage directory containing those
        requests, and if that is the only storage directory, also the top level
        parent directory.
        """
        log.debug('Cleaning up %s', self.session_dir)
        self.clear_requests()
        shutil.rmtree(self.session_dir, ignore_errors=True)
        try:
            # Attempt to remove the parent folder if it is empty
            os.rmdir(os.path.dirname(self.session_dir))
        except OSError:
            # Parent folder not empty
            pass

    def _cleanup_old_dirs(self) -> None:
        """Clean up and remove any old storage directories that were not previously
        cleaned up properly by cleanup().
        """
        parent_dir = os.path.dirname(self.session_dir)
        for storage_dir in os.listdir(parent_dir):
            storage_dir = os.path.join(parent_dir, storage_dir)
            try:
                if (
                    os.path.getmtime(storage_dir)
                    < (datetime.now() - timedelta(days=REMOVE_DATA_OLDER_THAN_DAYS)).timestamp()
                ):
                    shutil.rmtree(storage_dir, ignore_errors=True)
            except FileNotFoundError:
                # Can happen if multiple instances are run concurrently
                pass


class InMemoryRequestStorage:
    """Keeps request and response data in memory only.

    By default there is no limit on the number of requests that will be stored. This can
    be adjusted with the 'maxsize' attribute when creating a new instance.

    Instances are designed to be threadsafe.
    """

    def __init__(self, base_dir: Optional[str] = None, maxsize: Optional[int] = None):
        """Initialise a new InMemoryRequestStorage.

        Args:
            base_dir: The directory where certificate data is stored.
                If not specified, the system temp folder is used.
            maxsize: The maximum number of requests to store. Default no limit.
                When this attribute is set and the storage reaches the specified maximum
                size, old requests are discarded sequentially as new requests arrive.
        """
        if base_dir is None:
            base_dir = tempfile.gettempdir()

        self.home_dir: str = os.path.join(base_dir, '.seleniumwire')

        self._maxsize = sys.maxsize if maxsize is None else maxsize
        # OrderedDict doesn't support type hints before 3.7.2
        self._requests = OrderedDict()  # type: ignore
        self._lock = threading.Lock()

    def save_request(self, request: Request) -> None:
        """Save a request to storage.

        Args:
            request: The request to save.
        """
        request.id = str(uuid.uuid4())

        with self._lock:
            if self._maxsize > 0:
                while len(self._requests) >= self._maxsize:
                    self._requests.popitem(last=False)

                self._requests[request.id] = {
                    'request': request,
                }

    def save_response(self, request_id: str, response: Response) -> None:
        """Save a response to storage against a request with the specified id.

        Any certificate information will be attached to the original request
        against the request.cert attribute.

        Args:
            request_id: The id of the original request.
            response: The response to save.
        """
        request = self._get_request(request_id)

        if request is not None:
            request.response = response
            # The certificate data has been stored on the response but we make
            # it available on the request which is a more logical location.
            if hasattr(response, 'cert'):
                request.cert = response.cert
                del response.cert
        else:
            log.debug('Cannot save response as request %s is no longer stored' % request_id)

    def save_ws_message(self, request_id: str, message: WebSocketMessage) -> None:
        """Save a websocket message against a request with the specified id.

        Args:
            request_id: The id of the original handshake request.
            message: The websocket message to save.
        """
        request = self._get_request(request_id)

        if request is not None:
            request.ws_messages.append(message)

    def save_har_entry(self, request_id: str, entry: dict) -> None:
        """Save a HAR entry to storage against a request with the specified id.

        Args:
            request_id: The id of the original request.
            entry: The HAR entry to save.
        """
        with self._lock:
            try:
                v = self._requests[request_id]
                v['har_entry'] = entry
            except KeyError:
                log.debug('Cannot save HAR entry as request %s is no longer stored', request_id)

    def _get_request(self, request_id: str) -> Optional[Request]:
        """Get a request with the specified id or None if no request found."""
        with self._lock:
            try:
                return self._requests[request_id]['request']
            except KeyError:
                return None

    def load_requests(self) -> List[Request]:
        """Load all previously saved requests.

        The requests are returned as a list of request objects in the order in which they
        were saved.

        Note that for efficiency request objects are not copied when returned, so any
        change made to a request will also affect the stored version.

        Returns: A list of request objects.
        """
        with self._lock:
            return [v['request'] for v in self._requests.values()]

    def load_last_request(self) -> Optional[Request]:
        """Load the last saved request.

        Returns: The last saved request or None if no requests have
            yet been stored.
        """
        with self._lock:
            try:
                return next(reversed(self._requests.values()))['request']
            except (StopIteration, KeyError):
                return None

    def load_har_entries(self) -> List[dict]:
        """Load all previously saved HAR entries.

        Returns: A list of HAR entries.
        """
        with self._lock:
            return [v['har_entry'] for v in self._requests.values() if 'har_entry' in v]

    def iter_requests(self) -> Iterator[Request]:
        """Return an iterator over the saved requests.

        Returns: An iterator of request objects.
        """
        with self._lock:
            values = list(self._requests.values())

        for v in values:
            yield v['request']

    def clear_requests(self) -> None:
        """Clear all previously saved requests."""
        with self._lock:
            self._requests.clear()

    def find(self, pat: str, check_response: bool = True) -> Optional[Request]:
        """Find the first request that matches the specified pattern.

        Requests are searched in chronological order.

        Args:
            pat: A pattern that will be searched in the request URL.
            check_response: When a match is found, whether to check that the request has
                a corresponding response. Where check_response=True and no response has
                been received, this method will skip the request and continue searching.

        Returns: The first request in the storage that matches the pattern,
            or None if no requests match.
        """
        with self._lock:
            for v in self._requests.values():
                request = v['request']

                if re.search(pat, request.url):
                    if (check_response and request.response) or not check_response:
                        return request

        return None

    def cleanup(self) -> None:
        """Clear all previously saved requests."""
        self.clear_requests()
