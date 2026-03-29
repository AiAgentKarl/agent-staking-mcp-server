# agent-staking-mcp-server

**MCP server for agent reputation staking** — trust through skin-in-the-game.

Agents deposit stakes as trust collateral. Bad behavior gets slashed. Good actors build reputation over time. Creates a self-regulating trust layer for the agent economy.

## Why Staking?

Traditional reputation systems are cheap to game. Staking changes the incentive structure:
- **Agents that stake** signal commitment — they have something to lose
- **Slashing** punishes bad behavior with real consequences
- **Network effect** — the more agents stake, the more trustworthy the entire network becomes

## Tools

| Tool | Description |
|------|-------------|
| `tool_stake_deposit` | Deposit stake as trust collateral |
| `tool_stake_verify` | Check an agent's stake and trust tier |
| `tool_reputation_by_stake` | Get stake-weighted reputation score (0–100) |
| `tool_slash_stake` | Slash an agent's stake for bad behavior |
| `tool_dispute_open` | Open a dispute between two agents |
| `tool_dispute_resolve` | Resolve a dispute and auto-slash the loser |
| `tool_stake_leaderboard` | Ranked list of most trustworthy agents |

## Trust Tiers

| Balance | Tier |
|---------|------|
| 0 | unverified |
| 1–9 REP | bronze |
| 10–49 REP | silver |
| 50–199 REP | gold |
| 200+ REP | platinum |

## Installation

```bash
pip install agent-staking-mcp-server
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "agent-staking": {
      "command": "agent-staking-mcp-server"
    }
  }
}
```

## Example Usage

```
# Deposit stake
stake_deposit("agent-alice", 100, "REP")

# Verify trust
stake_verify("agent-alice")
# → balance: 100, trust_tier: "gold", trust_score: 50.0

# Open dispute
dispute_open("agent-alice", "agent-bob", "Bob failed to deliver, took payment", stake_at_risk=50.0)

# Resolve — Alice wins, Bob gets slashed
dispute_resolve("dispute_12345_agent-al", "agent-alice", "Evidence confirmed non-delivery")
# → agent-bob's stake reduced by 50 REP automatically

# Leaderboard
stake_leaderboard(top_n=5)
```

## How It Works

1. **Deposit**: Agents stake REP tokens to prove commitment
2. **Build trust**: Longevity + high balance + no slashes = high reputation score
3. **Slash**: Bad actors get penalized — slash events are permanent and public
4. **Disputes**: Structured conflict resolution with automatic stake enforcement
5. **Leaderboard**: Most trustworthy agents ranked for easy discovery

Data is stored locally in `~/.agent_staking_store.json` — persistent across restarts.

## Related Servers

- [agent-reputation-mcp-server](https://github.com/AiAgentKarl/agent-reputation-mcp-server) — Basic reputation tracking
- [shared-context-cache-mcp-server](https://github.com/AiAgentKarl/shared-context-cache-mcp-server) — Shared knowledge cache
- [agent-identity-mcp-server](https://github.com/AiAgentKarl/agent-identity-mcp-server) — Agent identity management

## License

MIT
