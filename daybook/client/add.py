""" Code for the add subcommand - which adds a transaction to a file.
"""

import csv
import os
import sys

import dateparser

from daybook.client.load import group_csvs
from daybook.Amount import Amount
from daybook.Hints import Hints
from daybook.Ledger import Ledger
from daybook.util.autoinput import autoinput


def get_fieldnames(csv_):
    """ Return fieldnames in the CSV as a list.
    """
    with open(csv_) as f:
        reader = csv.DictReader(f)
        return reader.fieldnames


def do_add(args):
    """ Entry point for the add subcommand.

    The csv and hints file are parsed so that the ledger contains
    enough information to assist with autocompletion.
    """
    ledger = Ledger(args.primary_currency)
    hints = None

    if os.path.exists(args.csv) and not os.path.isfile(args.csv):
        print('{} is not a regular file.'.format(args.csv))

    if not os.path.exists(args.csv):
        print('Creating {}.'.format(args.csv))
        with open(args.csv, 'w') as f:
            f.write('date,src,dest,amount,tags,notes\n')

    # check for existence of necessary headings
    headings = get_fieldnames(args.csv)

    if 'date' not in headings:
        print('ERROR: CSV {} requires at least a "date" field.'.format(args.csv))
        sys.exit(1)

    # load the ledger
    if args.hints:
        hints = Hints(args.hints)
        ledger.loadCsv(args.csv, hints, skipinvals=True)
    else:
        level = group_csvs(args.csv)[0]

        hints = level['hints']
        ledger.loadCsv(args.csv, hints, skipinvals=True)

    # create account name and currency suggestions
    currency_opts = set()
    account_opts = set()
    for account in ledger.accounts.values():
        account_opts.add('{}.{}'.format(account.type, account.name))
        currency_opts = currency_opts.union(account.balances.keys())

    if hints:
        account_opts = account_opts.union(hints.hints.values())

    # create tag suggestions
    tag_opts = set()
    for t in ledger.transactions:
        tag_opts = tag_opts.union(t.tags) if t.tags else tag_opts

    # Get input. Preserve field order and skip unrecognized fieldnames.
    line = []
    print('Adding a transaction to {}.'.format(args.csv))
    for heading in headings:

        if heading == 'date':
            if args.date:
                date = dateparser.parse(args.date)
            else:
                date = autoinput('Date (empty for today): ') or 'today'
                date = dateparser.parse(date)

            date = date.replace(microsecond=0)
            line.append('"{}"'.format(str(date)))
        elif heading in ['src', 'dest', 'target']:
            if heading == 'src' and args.src:
                acc = args.src
            elif heading == 'dest' and args.dest:
                acc = args.dest
            elif heading == 'target' and args.target:
                acc = args.target
            else:
                acc = autoinput('{} account (empty for "this"): '.format(heading), account_opts) or 'this'

            line.append('"{}"'.format(acc))
        elif heading == 'amount':
            amount = None
            if args.amount:
                try:
                    amount = Amount.createFromStr(args.amount)
                except ValueError as ve:
                    print('ERROR: You entered an invalid amount: {}'.format(ve))
                    sys.exit(1)
            else:
                scurr = ledger.primary_currency

                try:
                    samount = autoinput('Src amount (empty for 0.0): ') or 0.0
                    samount = float(samount)
                except ValueError:
                    print('ERROR: {} is not a number.'.format(samount))
                    sys.exit(1)

                scurr = autoinput('Src currency (empty for {}): '.format(scurr), currency_opts) or scurr

                try:
                    damount = autoinput('Dest amount (empty for {}): '.format(samount)) or samount
                    damount = float(damount)
                except ValueError:
                    print('ERROR: {} is not a number.'.format(damount))
                    sys.exit(1)

                dcurr = autoinput('Dest currency (empty for {}): '.format(scurr), currency_opts) or scurr

                try:
                    amount = Amount(scurr, samount, dcurr, damount)
                except ValueError as ve:
                    print('ERROR: Entering amount: {}'.format(ve))
                    sys.exit(1)
            line.append('"{}"'.format(amount))
        elif heading == 'tags':
            if args.tags:
                tags = args.tags
            else:
                tags = autoinput('Tags - colon separated (empty for None): ', tag_opts)

            tags = ':'.join([x.strip() for x in tags.split(':')])
            line.append('"{}"'.format(tags))
        elif heading == 'notes':
            if args.notes:
                notes = args.notes
            else:
                notes = autoinput('Notes (empty for None): ')
            line.append('"{}"'.format(notes))
        else:
            line.append('""')

    line = ','.join(line)
    with open(args.csv, 'a') as f:
        f.write(line + '\n')
