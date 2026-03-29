"""
Agent Staking MCP Server — Vertrauen durch Skin-in-the-Game.

Agents hinterlegen Stakes als Vertrauensbeweis. Schlechtes Verhalten
wird mit Stake-Slash bestraft. Streitfaelle werden transparent aufgeloest.
"""

from mcp.server.fastmcp import FastMCP

from agent_staking_mcp_server.tools.staking import (
    dispute_open,
    dispute_resolve,
    reputation_by_stake,
    slash_stake,
    stake_deposit,
    stake_leaderboard,
    stake_verify,
)

# MCP-Server initialisieren
mcp = FastMCP(
    "agent-staking-mcp-server",
    instructions=(
        "MCP server for agent reputation staking. Agents deposit stakes as trust collateral — "
        "bad behavior gets slashed, good actors build trust over time. Tools: stake_deposit, "
        "stake_verify, reputation_by_stake, slash_stake, dispute_open, dispute_resolve, stake_leaderboard."
    ),
)


@mcp.tool()
def tool_stake_deposit(agent_id: str, amount: float, currency: str = "REP") -> dict:
    """
    Deposit stake for an agent as a trust proof.

    Higher stake = higher trust tier. Tiers: unverified → bronze → silver → gold → platinum.
    Stake can be slashed for bad behavior.

    Args:
        agent_id: Unique identifier for the agent (e.g. DID, UUID, name)
        amount: Amount to stake (must be > 0)
        currency: Currency/token for the stake (default: REP)
    """
    return stake_deposit(agent_id, amount, currency)


@mcp.tool()
def tool_stake_verify(agent_id: str) -> dict:
    """
    Verify an agent's stake status and trust level.

    Returns current balance, trust tier, slash history, and trust score.

    Args:
        agent_id: Agent identifier to look up
    """
    return stake_verify(agent_id)


@mcp.tool()
def tool_reputation_by_stake(agent_id: str) -> dict:
    """
    Get a stake-weighted reputation score for an agent (0-100).

    Combines stake size, slash history, and membership duration.
    Returns score, grade (A+ to F), and breakdown.

    Args:
        agent_id: Agent identifier to evaluate
    """
    return reputation_by_stake(agent_id)


@mcp.tool()
def tool_slash_stake(agent_id: str, slash_amount: float, reason: str) -> dict:
    """
    Slash an agent's stake for bad behavior (fraud, non-delivery, rule violations).

    The slash is permanently recorded in the agent's history.
    Slash events reduce the agent's trust score and tier.

    Args:
        agent_id: Agent to slash
        slash_amount: Amount to slash from their stake
        reason: Description of the bad behavior (logged permanently)
    """
    return slash_stake(agent_id, slash_amount, reason)


@mcp.tool()
def tool_dispute_open(
    claimant_id: str,
    defendant_id: str,
    description: str,
    stake_at_risk: float = 0.0,
) -> dict:
    """
    Open a dispute between two agents.

    If the defendant loses, their stake is automatically slashed
    by the stake_at_risk amount.

    Args:
        claimant_id: Agent filing the complaint
        defendant_id: Agent being accused
        description: What happened (will be permanently logged)
        stake_at_risk: Amount of defendant's stake to slash if they lose
    """
    return dispute_open(claimant_id, defendant_id, description, stake_at_risk)


@mcp.tool()
def tool_dispute_resolve(
    dispute_id: str,
    winner_id: str,
    resolution_notes: str,
) -> dict:
    """
    Resolve an open dispute and optionally slash the loser's stake.

    If claimant wins, defendant's stake is automatically slashed
    by the disputed amount.

    Args:
        dispute_id: ID of the dispute to resolve (from dispute_open)
        winner_id: Agent ID of the winner (claimant or defendant)
        resolution_notes: Explanation of the resolution decision
    """
    return dispute_resolve(dispute_id, winner_id, resolution_notes)


@mcp.tool()
def tool_stake_leaderboard(top_n: int = 10) -> dict:
    """
    Get the trust leaderboard — top staked agents ranked by trust score.

    Shows the most trustworthy agents in the network. Higher stake +
    no slashes + longer membership = better ranking.

    Args:
        top_n: Number of agents to show (default: 10)
    """
    return stake_leaderboard(top_n)


def main():
    """Startet den MCP-Server ueber stdio-Transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
