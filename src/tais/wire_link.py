"""Controlled link experiments on copies of *already uploaded* envelopes.

No algorithm/generator access; all exactness checks occur outside Receiver.
"""
from dataclasses import dataclass
import hashlib
import struct
from . import wire_codec as v1
from .wire_v2 import Sender, Receiver

LINK_SEED = 2026101807
PROFILES = ('loss0','loss1','loss5','loss10','burst','sender_restart','receiver_restart')
PERIODS = (8,16,32)
EVENT_COLUMNS = ('index','timestamp','device','session','sequence','kind','v1_bytes','v2_bytes',
                 'link_action','receiver_status','gap','recovered','restored_envelope_sha256','v2_hex')


def exact(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,float):return struct.pack('>d',a)==struct.pack('>d',b)
    if isinstance(a,dict):return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    return a==b


def discarded(profile, seed, scenario, index, timestamp):
    if profile=='burst':return 5<=index<9 or 21<=index<25
    if profile in ('loss1','loss5','loss10'):
        percent=int(profile[4:])
        token=f'{LINK_SEED}|{seed}|{scenario}|{timestamp}'.encode()
        uniform=int.from_bytes(hashlib.sha256(token).digest()[:8],'big')
        return uniform*100 < percent*(1<<64)
    if profile not in PROFILES:raise ValueError('Unknown link profile')
    return False


@dataclass(frozen=True)
class Packet:
    wire: bytes
    session: int
    sequence: int
    keyframe: bool
    header_bytes: int
    identity_bytes: int
    refresh_premium: int


def encode_stream(envelopes, period, restart=False):
    sender=Sender(period=period)
    packets=[]
    for i,e in enumerate(envelopes):
        if restart and i==20:sender.restart(2)
        wire=sender.encode(e);a=sender.last_accounting
        packets.append(Packet(wire,a['session'],a['sequence'],a['keyframe'],
                              a['outer_header_crc_bytes'],a['identity_sequence_bytes'],a['key_refresh_premium']))
    return packets


class _Waits:
    def __init__(self):self.start=None;self.episodes=[]
    def update(self, index, timestamp, missing):
        if missing and self.start is None:self.start=index,timestamp
        if not missing and self.start is not None:
            i,t=self.start
            self.episodes.append(dict(start_index=i,start_s=t,end_index=index,end_s=timestamp,
                                      wait_frames=index-i,wait_s=timestamp-t,censored=False))
            self.start=None
    def finish(self, count, timestamp):
        if self.start is not None:
            i,t=self.start
            self.episodes.append(dict(start_index=i,start_s=t,end_index=None,end_s=None,
                                      wait_frames=count-1-i,wait_s=timestamp-t,censored=True))


def simulate(envelopes, packets, v1_frames, profile, seed, scenario, hashes):
    """Actually parse every delivered v2 packet in a fresh receiver.

    V1 frames are bit-identical across profiles and validated by caller once;
    stateless success is unaffected by preceding packet delivery.
    """
    if profile not in PROFILES:raise ValueError('Unknown profile')
    if not (len(envelopes)==len(packets)==len(v1_frames)==len(hashes)):
        raise ValueError('Input stream length mismatch')
    receiver=Receiver();stats=dict(sent=len(envelopes),v1_bytes=sum(map(len,v1_frames)),v2_bytes=0,
        dropped=0,received=0,v1_decoded=0,v2_decoded=0,received_unrestored=0,permanently_missing_v2=0,
        continuity_gap_receipts=0,observed_sequence_gaps=0,receiver_recovered=0,
        keys=0,deltas=0,key_bytes=0,delta_bytes=0,outer_header_crc_bytes=0,identity_sequence_bytes=0,
        refresh_premium_bytes=0,initialization_key_bytes=0,periodic_key_bytes=0,
        sender_restarts=0,receiver_restarts=0)
    waits={'v1':_Waits(),'v2':_Waits()};events=[]
    for i,(e,p,old,ehash) in enumerate(zip(envelopes,packets,v1_frames,hashes)):
        if profile=='receiver_restart' and i==20:
            receiver.reset();stats['receiver_restarts']+=1
        if profile=='sender_restart' and i==20:stats['sender_restarts']+=1
        stats['v2_bytes']+=len(p.wire)
        stats['keys' if p.keyframe else 'deltas']+=1
        stats['key_bytes' if p.keyframe else 'delta_bytes']+=len(p.wire)
        stats['outer_header_crc_bytes']+=p.header_bytes
        stats['identity_sequence_bytes']+=p.identity_bytes
        stats['refresh_premium_bytes']+=p.refresh_premium
        if p.keyframe:stats['initialization_key_bytes' if p.sequence==0 else 'periodic_key_bytes']+=len(p.wire)
        dropped=discarded(profile,seed,scenario,i,e['timestamp'])
        if dropped:
            stats['dropped']+=1;status='NOT_RECEIVED';got=None;gap=0;recovered=False
        else:
            stats['received']+=1;stats['v1_decoded']+=1
            result=receiver.receive(p.wire)
            status,got,gap,recovered=result.status,result.envelope,result.gap,result.recovered
            stats['continuity_gap_receipts']+=gap>0;stats['observed_sequence_gaps']+=gap
            stats['receiver_recovered']+=recovered
            if got is None:stats['received_unrestored']+=1
            else:
                if not exact(got,e):raise AssertionError('A complete receiver envelope is wrong')
                stats['v2_decoded']+=1
        waits['v1'].update(i,e['timestamp'],dropped)
        waits['v2'].update(i,e['timestamp'],got is None)
        events.append([i,e['timestamp'],1,p.session,p.sequence,'K' if p.keyframe else 'D',len(old),len(p.wire),
                       'DROP' if dropped else 'RECEIVE',status,gap,recovered,ehash if got is not None else None,p.wire.hex()])
    stats['permanently_missing_v2']=stats['sent']-stats['v2_decoded']
    assert stats['permanently_missing_v2']==stats['dropped']+stats['received_unrestored']
    assert stats['v1_decoded']+stats['dropped']==stats['sent']
    assert stats['keys']+stats['deltas']==stats['sent']
    assert stats['key_bytes']+stats['delta_bytes']==stats['v2_bytes']
    episodes=[]
    for codec,tracker in waits.items():
        tracker.finish(len(envelopes),envelopes[-1]['timestamp'] if envelopes else 0)
        episodes.extend(dict(codec=codec,**e) for e in tracker.episodes)
    return stats,episodes,events
