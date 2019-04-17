import time

def doc_feeder(collection, step=1000, s=None, e=None, inbatch=False, query=None, batch_callback=None, fields=None):
    '''A iterator for returning docs in a collection, with batch query.
       additional filter query can be passed via "query", e.g.,
       doc_feeder(collection, query={'taxid': {'$in': [9606, 10090, 10116]}})
       batch_callback is a callback function as fn(cnt, t), called after every batch
       fields is optional parameter passed to find to restrict fields to return.
    '''
    cur = collection.find(query, timeout=False, fields=fields)
    n = cur.count()
    s = s or 0
    e = e or n
    print('Retrieving %d documents from database "%s".' % (n, collection.name))
    t0 = time.time()
    if inbatch:
        doc_li = []
    cnt = 0
    t1 = time.time()
    try:
        if s:
            cur.skip(s)
            cnt = s
            print("Skipping %d documents." % s)
        if e:
            cur.limit(e - (s or 0))
        cur.batch_size(step)
        print("Processing %d-%d documents..." % (cnt + 1, min(cnt + step, e)), end='')
        for doc in cur:
            if inbatch:
                doc_li.append(doc)
            else:
                yield doc
            cnt += 1
            if cnt % step == 0:
                if inbatch:
                    yield doc_li
                    doc_li = []
                print('Done.[%.1f%%,%s]' % (cnt * 100. / n, timesofar(t1)))
                if batch_callback:
                    batch_callback(cnt, time.time()-t1)
                if cnt < e:
                    t1 = time.time()
                    print("Processing %d-%d documents..." % (cnt + 1, min(cnt + step, e)), end='')
        if inbatch and doc_li:
            #Important: need to yield the last batch here
            yield doc_li

        #print 'Done.[%s]' % timesofar(t1)
        print('Done.[%.1f%%,%s]' % (cnt * 100. / n, timesofar(t1)))
        print("=" * 20)
        print('Finished.[total time: %s]' % timesofar(t0))
    finally:
        cur.close()

def ask(prompt, options='YN'):
    '''Prompt Yes or No,return the upper case 'Y' or 'N'.
    '''
    options = options.upper()
    while 1:
        s = input(prompt+'[%s]' % '|'.join(list(options))).strip().upper()
        if s in options:
            break
    return s


def timesofar(t0, clock=0, t1=None):
    '''return the string(eg.'4m5.32s') for the passed real time/CPU time so far
       from given t0 (clock 0 for cpu time 1 for realtime).
    '''
    t1 = t1 or time.clock() if clock else time.time()
    t = t1 - t0
    h = int(t / 3600)
    m = int((t % 3600) / 60)
    s = round((t % 3600) % 60, 2)
    t_str = ''
    if h != 0:
        t_str += '%sh' % h
    if m != 0:
        t_str += '%sm' % m
    t_str += '%ss' % s
    return t_str