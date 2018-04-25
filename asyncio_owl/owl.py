#!/usr/bin/env python3.6
import asyncio
import logging

import aiohttp
import tqdm

URL_BASE = "https://api.overwatchleague.com/"
URL_LIVE_MATCH = "https://api.overwatchleague.com/live-match"
URL_TEAMS = "https://api.overwatchleague.com/teams"
URL_TEAM = "https://api.overwatchleague.com/team/{}"
URL_RANKINGS = "https://api.overwatchleague.com/ranking"
URL_STANDINGS = "https://api.overwatchleague.com/v2/standings"
URL_MATCHES = "https://api.overwatchleague.com/matches"
URL_MATCH = "https://api.overwatchleague.com/match/{}"
URL_SCHEDULE = "https://api.overwatchleague.com/schedule"
URL_STREAMS = "https://api.overwatchleague.com/streams"
URL_VODS = "https://api.overwatchleague.com/vods"
URL_MAPS = "https://api.overwatchleague.com/maps"
URL_NEWS = "https://api.overwatchleague.com/news"
URL_VIDEOS = "https://api.overwatchleague.com/playlist/owl-app-playlist"

# The max tcp connection we open
MAX_CONNECTION = 1000

# setting up logger
logger = logging.getLogger(__name__)
console = logging.StreamHandler()
logger.addHandler(console)


class ClientOWL(aiohttp.ClientSession):
    def __init__(self, queue_size=10, progress_bar=False, debug=False, num_dlq_consumers=10, **kwargs):
        super(ClientOWL, self).__init__(**kwargs)
        self.queue_size = queue_size
        self.connector_limit = self.connector.limit
        self._responses = []
        self.progress_bar = progress_bar
        self.num_dlq_consumers = num_dlq_consumers
        if debug:
            logger.setLevel(logging.DEBUG)

    async def single_download(self, url, item=None):
        if item is not None:
            url = url.format(item)
        async with self.get(url) as resp:
            return await resp.json()

    async def multi_download(self, itr, url, num_of_consumers=None, desc=""):
        queue, dlq, responses = asyncio.Queue(
            maxsize=self.queue_size), asyncio.Queue(), []
        num_of_consumers = num_of_consumers or min(self.connector_limit, self.try_get_itr_len(itr))
        consumers = [asyncio.ensure_future(
            self._consumer(main_queue=queue, dlq=dlq, responses=responses)) for _ in
                     range(num_of_consumers or self.connector_limit)]
        dlq_consumers = [asyncio.ensure_future(
            self._consumer(dlq, dlq, responses)) for _ in range(self.num_dlq_consumers)]
        produce = await self._produce(itr, url, queue, desc=desc)
        await queue.join()
        await dlq.join()
        for consumer in consumers + dlq_consumers:
            consumer.cancel()
        return responses

    def try_get_itr_len(self, itr):
        try:
            return len(itr)
        except TypeError:
            return 1000000

    async def _produce(self, items, base_url, queue, desc=""):
        for item in tqdm.tqdm(items, desc=desc + " (Estimation)", disable=not self.progress_bar):
            await queue.put(base_url.format(item))

    async def _consumer(self, main_queue, dlq, responses):
        while True:
            try:
                url = await main_queue.get()
                async with self.get(url, timeout=10) as response:
                    resp = response
                    resp.raise_for_status()
                    responses.append(await resp.json())
                    # Notify the queue that the item has been processed
                    main_queue.task_done()

            except (asyncio.TimeoutError) as e:
                logger.debug("Problem with %s, Moving to DLQ" % url)
                await dlq.put(url)
                main_queue.task_done()

    async def teams(self):
        return await self.single_download(URL_TEAMS)

    async def ranking(self):
        return await self.single_download(URL_RANKINGS)

    async def standings(self):
        return await self.single_download(URL_STANDINGS)

    async def matches(self):
        return await self.single_download(URL_MATCHES)

    async def schedule(self, stage=-1, week=-1):
        schedule_data = await self.single_download(URL_SCHEDULE)
        if stage >= 0:
            try:
                if week >= 0:
                    return schedule_data["data"]["stages"][stage]["weeks"][week]
                else:
                    return schedule_data["data"]["stages"][stage]
            except IndexError:
                return "{'success': False, 'message': 'Could not find requested schedule'}"
        else:
            return schedule_data["data"]["stages"]

    async def vods(self):
        return await self.single_download(URL_VODS)

    async def maps(self):
        return await self.single_download(URL_MAPS)

    async def news(self):
        return await self.single_download(URL_NEWS)

    async def videos(self):
        return await self.single_download(URL_VIDEOS)

    async def team(self, team_id):
        return await self.single_download(URL_TEAM, team_id)

    async def match(self, match_id):
        return await self.single_download(URL_MATCH, match_id)

    async def live_match(self, match_type=None):
        match_data = await self.single_download(URL_LIVE_MATCH)
        if match_type is not None:
            return match_data["data"][match_type]
        return match_data["data"]
