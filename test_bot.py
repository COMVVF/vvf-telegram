import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import bot

class Tests(unittest.TestCase):
    def test_changes(self):
        with tempfile.TemporaryDirectory() as d:
            item = dict(url=bot.BASE+'/media/notizie/a', title='Circolare', description='A', date='', category='Circolari')
            with patch.object(bot,'STATE',Path(d)/'state.json'), patch.object(bot,'download',return_value=b'x'), patch.object(bot,'rss',return_value=[item]), patch.object(bot,'page_items',return_value=[item]), patch.object(bot,'telegram') as send, patch.dict(bot.os.environ,TELEGRAM_CHAT_ID='-1'), patch.object(bot.time,'sleep'):
                bot.run(); send.assert_not_called()
                bot.run(); send.assert_not_called()
                item['description']='B'; send.side_effect=RuntimeError('403')
                with self.assertRaises(RuntimeError): bot.run()
                send.side_effect=None; bot.run(); self.assertEqual(send.call_count,2)
                bot.run(); self.assertEqual(send.call_count,2)
    def test_parsers(self):
        self.assertIsNone(bot.canonical('https://example.com'))
        self.assertIsNone(bot.category('Incendio autovettura','Intervento a Fano','/direzione-regionale/notizie/a'))
        items=bot.rss(b'<rss><channel><item><title>Circolare</title><link>http://www.vigilfuoco.it/media/notizie/a</link><pubdate>oggi</pubdate></item></channel></rss>')
        self.assertEqual(items[0]['date'],'oggi')
        source=dict(url=bot.BASE+'/x',prefix='/x/',category='Test')
        self.assertEqual(len(bot.page_items(b'<nav><a href="/x/out">out</a></nav><main><a href="/x/in">Nuovo documento</a></main>',source)),1)

if __name__=='__main__': unittest.main()
