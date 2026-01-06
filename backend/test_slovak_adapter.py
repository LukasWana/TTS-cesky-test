#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for Czech→Slovak phonetic adapter
"""

from cz_sk_adapter import get_adapter

def test_adapter():
    """Test the Czech to Slovak adapter with various examples"""

    adapter = get_adapter()

    # Test cases
    test_cases = [
        "Příliš žlutoučký kůň úpěl dábelské ódy.",
        "Dnes jsem jel autem do Prahy.",
        "Běžel jsem rychle kolem domu.",
        "Líbí se mi tato kniha.",
        "Můj přítel dělá dobrou práci.",
        "Kůň běžel rychle přes pole.",
        "Dělám si večeři a potom půjdu spát.",
        "Můžeš mi pomoct s tímto úkolem?",
    ]

    print("=" * 80)
    print("CZECH TO SLOVAK PHONETIC ADAPTER TEST")
    print("=" * 80)
    print()

    for test_text in test_cases:
        result = adapter.convert(test_text)

        print(f"CZECH:    {result.original}")
        print(f"SLOVAK:   {result.converted}")
        print(f"Changes:  {result.changes_count} words converted")
        print(f"Confidence: {result.confidence:.1%}")

        if result.applied_conversions:
            conversions = ", ".join([
                f"'{c['original']}' -> '{c['converted']}'"
                for c in result.applied_conversions[:3]
            ])
            more = f" (+{len(result.applied_conversions) - 3} more)" if len(result.applied_conversions) > 3 else ""
            print(f"Examples: {conversions}{more}")

        print()

    print("=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_adapter()
