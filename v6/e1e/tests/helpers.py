import json

from tests import fixtures  # noqa: F401  (sets sys.path)
from e1e import Publisher, Receiver, E1EError, canonical, make_delta, sha256_hex
from tests.fixtures import V1, V2_DELTA, V3_DELTA


def build():
    pub = Publisher()
    d1, f1 = pub.publish(V1)
    d2, f2 = pub.publish(V2_DELTA)
    d3, f3 = pub.publish(V3_DELTA)
    return pub, (d1, d2, d3), (f1, f2, f3)


def recv_at(fulls, i):
    r = Receiver()
    r.load_full(fulls[i])
    return r


def redigest_delta(obj):
    """Re-seal a tampered delta so only the targeted check can fire."""
    body = {k: v for k, v in obj.items() if k != "digest"}
    body["digest"] = sha256_hex(canonical(body))
    return canonical(body)


class RejectMixin:
    def assertRejected(self, holder, fn, code):
        before = holder.state.fingerprint()
        with self.assertRaises(E1EError) as cm:
            fn()
        self.assertEqual(cm.exception.code, code, cm.exception)
        self.assertEqual(holder.state.fingerprint(), before, "rejected op changed state")
