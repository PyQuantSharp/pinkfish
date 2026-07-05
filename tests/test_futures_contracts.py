"""Tests for CME micro futures contract selection."""

import datetime
import unittest

from pinkfish.signals.futures import (
    format_contract,
    futures_lines,
    third_friday,
    trade_contract,
)


class TestFuturesContracts(unittest.TestCase):

    def test_third_friday_june_2026(self):
        self.assertEqual(third_friday(2026, 6), datetime.date(2026, 6, 19))

    def test_may_uses_june_contract(self):
        contract, expiry = trade_contract('MES', datetime.date(2026, 5, 15))
        self.assertEqual(contract, '/MESM26')
        self.assertEqual(expiry, datetime.date(2026, 6, 19))

    def test_early_june_skips_expiring_month(self):
        contract, expiry = trade_contract('MES', datetime.date(2026, 6, 1))
        self.assertEqual(contract, '/MESU26')
        self.assertEqual(expiry, third_friday(2026, 9))

    def test_march_roll_month_skips_to_june(self):
        contract, _ = trade_contract('MES', datetime.date(2026, 3, 2))
        self.assertEqual(contract, '/MESM26')

    def test_after_june_expiry_uses_september(self):
        contract, _ = trade_contract('MES', datetime.date(2026, 6, 22))
        self.assertEqual(contract, '/MESU26')

    def test_mnq_symbol_format(self):
        contract, _ = trade_contract('MNQ', datetime.date(2026, 2, 10))
        self.assertEqual(contract, '/MNQH26')

    def test_roll_ok_when_long_before_roll_window(self):
        lines = futures_lines('/MES', datetime.date(2026, 6, 5), 'LONG')
        self.assertEqual(lines[0], 'Contract: /MESU26 (expires 2026-09-18)')
        self.assertEqual(lines[1], 'Roll: OK')

    def test_roll_warning_eight_days_before_expiry(self):
        lines = futures_lines('/MES', datetime.date(2026, 6, 12), 'LONG')
        self.assertTrue(lines[0].startswith('Contract: /MESU26'))
        self.assertTrue(lines[1].startswith('Roll: ROLL — close /MESM26, open /MESU26'))

    def test_flat_shows_contract_only(self):
        lines = futures_lines('/MES', datetime.date(2026, 6, 12), 'FLAT')
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('Contract: /MESU26'))

    def test_format_contract_uppercase(self):
        self.assertEqual(format_contract('mes', 2026, 6), '/MESM26')


if __name__ == '__main__':
    unittest.main()
