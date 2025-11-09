from ..core.cache import InMemoryCache
from ..core.db import DB
from ..core.audit import Audit

class ProfileAgent:
    def __init__(self, cache: InMemoryCache, db: DB, audit: Audit):
        self.cache, self.db, self.audit = cache, db, audit

    def run(self, ctx: dict) -> dict:
        email = ctx["profile"].get("email")
        if not email:
            ctx["errors"] = ctx.get("errors", []) + ["email is required"]
            return ctx
        cached = self.cache.get(email)
        if cached:
            ctx["profile"] = {**cached, **ctx["profile"]}
            self.audit.info(email, "profile_cache_hit", "merged cached + input")
        else:
            dbp = self.db.get_profile(email)
            if dbp:
                ctx["profile"] = {**dbp, **ctx["profile"]}
                self.cache.set(email, dbp)
                self.audit.info(email, "profile_db_hit", "merged db + input")
        # save/update
        self.db.save_profile(email, ctx["profile"])
        self.cache.set(email, ctx["profile"])
        self.audit.info(email, "profile_upsert", "stored profile")
        return ctx
