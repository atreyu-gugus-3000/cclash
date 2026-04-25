# Networking and security v0.1

cclash should support local-network play without becoming a security problem.

## 1. Scope

MVP networking is LAN-only.

```text
same local network
one host
multiple clients
no global servers
no account system
no real API tokens
```

## 2. Architecture

Recommended MVP:

```text
LAN Host
├─ matchmaking
├─ match state
├─ daily claims, optional later
├─ trades, later
└─ card ledger, later

Clients
├─ render UI
├─ submit intentions
└─ receive authoritative state
```

The Host is authoritative.

Clients do not calculate final results and then claim they are true. Clients only send intended actions.

Example:

```text
Client: play event Rotate90
Host: validates ownership and legality
Host: mutates grid
Host: broadcasts new state
```

## 3. Discovery

Use mDNS / Bonjour first.

Service name:

```text
_cclash._tcp.local
```

Fallback:

```text
cclash join 192.168.1.42
```

## 4. Pairing

Discovery may be open. Joining should not be automatic.

First connection uses a pairing code.

```text
Samuel invites you to cclash.

Pairing code: 482-119

Enter code:
>
```

After pairing, the client public key is remembered.

## 5. Identity

Each player has a local identity.

```text
player_id
public_key
private_key, local only
nickname
created_at
```

The private key never leaves the machine.

## 6. Signed actions

Important actions should be signed.

Examples:

```text
submit_compile
play_event
confirm_hardcore
accept_trade, later
claim_daily, later
```

Action payload:

```json
{
  "type": "play_event",
  "player_id": "player_123",
  "match_id": "match_456",
  "event_instance_id": "card_789",
  "nonce": 42,
  "signature": "..."
}
```

## 7. Replay protection

Every signed action gets a nonce.

The Host rejects:

- duplicate nonces
- old match IDs
- actions from unknown keys
- actions that do not match the current game state

## 8. No executable card effects

Card effects are data, never code.

Good:

```yaml
effect:
  type: modify_out
  target: friendly_codes_in_row
  amount: 1
```

Bad:

```yaml
effect: "enemy.hp -= 3"
```

The effect engine interprets a fixed whitelist of effect types.

## 9. Version compatibility

Before a match starts, host and client compare:

```text
rules_version
cardset_id
cardset_version
cardset_hash
```

If these do not match, the match is rejected.

## 10. Secrets

cclash must never transmit:

- OpenAI / Anthropic / GitHub API keys
- ChatGPT subscription tokens
- OS secrets
- SSH keys
- private keys

If a player identity is derived from a local secret, only a hash-derived public player ID is shared.

## 11. Local ledger

Cards are concrete instances.

```text
card_instance_id
card_id
owner_id
created_at
source
status
signature, later
```

In early MVP, this can be trusted locally.

Later, the Host can sign daily claims and trades.

## 12. Threat model, MVP

We protect against:

- accidental remote execution
- random LAN devices joining games
- simple action spoofing
- cardset mismatch
- accidental secret exposure

We do not fully protect against:

- a player editing their own local database
- malicious custom clients
- global cheating

This is acceptable for MVP because cclash is local, playful, and LAN-first.

## 13. Audit command, later

```text
cclash audit archive
```

Possible output:

```text
Archive audit:
143 valid cards
0 invalid cards
2 burned items
OK
```
