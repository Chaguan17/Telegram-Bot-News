import unittest
import asyncio
from bot.cron_service import run_news_cron_async
from bot.repositories.d1_binding_repository import D1BindingRepository

class BugReproductionTests(unittest.IsolatedAsyncioTestCase):
    
    async def test_reproduce_global_amnesia_fix(self):
        """
        Verifica que el envío a un usuario NO bloquee a otro.
        Antes: news_sent era 1 porque el primer éxito marcaba la noticia como enviada globalmente.
        Ahora: news_sent debe ser 1 (porque es una noticia), pero AMBOS usuarios deben recibir el mensaje.
        """
        sent_to = []
        marked_for = []
        
        # Simulamos 2 usuarios
        usuarios = [111, 222]
        # La noticia 'abc' ya fue enviada al usuario 111, pero NO al 222
        sent_history = {( "abc", 111 )} 

        async def is_news_sent(h, uid): return (h, uid) in sent_history
        async def mark_news_sent(h, uid): marked_for.append((h, uid))
        async def send_message(uid, msg): sent_to.append(uid)

        result = await run_news_cron_async(
            buscar_noticias=lambda: [{"hash": "abc", "message": "test"}],
            get_news_subscribers=lambda: usuarios,
            is_news_sent=is_news_sent,
            mark_news_sent=mark_news_sent,
            send_message=send_message,
            update_bot_health=lambda s: None
        )

        # DEBE haberse enviado al usuario 222
        self.assertIn(222, sent_to)
        # NO DEBE haberse enviado al 111 (ya la tenía)
        self.assertNotIn(111, sent_to)
        # Se debe haber marcado como enviada para el 222
        self.assertIn(("abc", 222), marked_for)
        print("\nOK: Bug 'Amnesia Global' verificado: Los envíos son independientes.")

    async def test_reproduce_phantom_result_fix(self):
        """
        Simula el bug de PyProxy en Cloudflare donde is_news_sent devolvía True 
        aunque la tabla estuviera vacía.
        """
        # Simulamos un objeto que NO es None pero representa un resultado vacío (el 'fantasma')
        phantom_row = {} 
        
        class MockDB:
            def prepare(self, sql): return self
            def bind(self, *p): return self
            async def first(self): return phantom_row

        repo = D1BindingRepository(MockDB())
        
        # Nuestra lógica nueva debe detectar que {} NO es una noticia enviada
        is_sent = await repo.is_news_sent("abc", 123)
        
        self.assertFalse(is_sent, "El bot detectó falsamente una noticia enviada debido a un objeto vacío")
        print("OK: Bug 'Fantasma de Pyodide' verificado: Los objetos vacíos no bloquean el envío.")

if __name__ == "__main__":
    unittest.main()
