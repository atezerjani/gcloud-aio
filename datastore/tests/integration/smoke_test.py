import asyncio
import uuid

import aiohttp
import pytest
from gcloud.aio.datastore import Datastore
from gcloud.aio.datastore import Filter
from gcloud.aio.datastore import GQLQuery
from gcloud.aio.datastore import Key
from gcloud.aio.datastore import Operation
from gcloud.aio.datastore import PathElement
from gcloud.aio.datastore import Projection
from gcloud.aio.datastore import PropertyFilter
from gcloud.aio.datastore import PropertyFilterOperator
from gcloud.aio.datastore import Query
from gcloud.aio.datastore import Value
from gcloud.aio.storage import Storage  # pylint: disable=no-name-in-module


@pytest.mark.asyncio  # type: ignore
async def test_item_lifecycle(creds: str, kind: str, project: str) -> None:
    key = Key(project, [PathElement(kind)])

    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        allocatedKeys = await ds.allocateIds([key], session=s)
        assert len(allocatedKeys) == 1
        key.path[-1].id = allocatedKeys[0].path[-1].id
        assert key == allocatedKeys[0]

        await ds.reserveIds(allocatedKeys, session=s)

        props_insert = {'is_this_bad_data': True}
        await ds.insert(allocatedKeys[0], props_insert, session=s)
        actual = await ds.lookup([allocatedKeys[0]], session=s)
        assert actual['found'][0].entity.properties == props_insert

        props_update = {'animal': 'aardvark', 'overwrote_bad_data': True}
        await ds.update(allocatedKeys[0], props_update, session=s)
        actual = await ds.lookup([allocatedKeys[0]], session=s)
        assert actual['found'][0].entity.properties == props_update

        props_upsert = {'meaning_of_life': 42}
        await ds.upsert(allocatedKeys[0], props_upsert, session=s)
        actual = await ds.lookup([allocatedKeys[0]], session=s)
        assert actual['found'][0].entity.properties == props_upsert

        await ds.delete(allocatedKeys[0], session=s)
        actual = await ds.lookup([allocatedKeys[0]], session=s)
        assert len(actual['missing']) == 1


@pytest.mark.asyncio  # type: ignore
async def test_transaction(creds: str, kind: str, project: str) -> None:
    key = Key(project, [PathElement(kind, name=f'test_record_{uuid.uuid4()}')])

    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        transaction = await ds.beginTransaction(session=s)
        actual = await ds.lookup([key], transaction=transaction, session=s)
        assert len(actual['missing']) == 1

        mutations = [
            ds.make_mutation(Operation.INSERT, key,
                             properties={'animal': 'three-toed sloth'}),
            ds.make_mutation(Operation.UPDATE, key,
                             properties={'animal': 'aardvark'}),
        ]
        await ds.commit(mutations, transaction=transaction, session=s)

        actual = await ds.lookup([key], session=s)
        assert actual['found'][0].entity.properties == {'animal': 'aardvark'}


@pytest.mark.asyncio  # type: ignore
async def test_rollback(creds: str, project: str) -> None:
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        transaction = await ds.beginTransaction(session=s)
        await ds.rollback(transaction, session=s)

@pytest.mark.asyncio  # type: ignore
async def test_query_with_key_projection(creds: str, kind: str,
                                         project: str) -> None:
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)
        # setup test data
        await ds.insert(Key(project, [PathElement(kind)]), {'value': 30}, s)
        property_filter = PropertyFilter(
            prop='value', operator=PropertyFilterOperator.EQUAL,
            value=Value(30))
        projection = [Projection.from_repr({'property': {'name': '__key__'}})]

        query = Query(kind=kind, query_filter=Filter(property_filter), limit=1,
                      projection=projection)
        result = await ds.runQuery(query, session=s)
        assert result.entity_results[0].entity.properties == {}
        assert result.entity_result_type.value == 'KEY_ONLY'
        # clean up test data
        await ds.delete(result.entity_results[0].entity.key, s)

@pytest.mark.asyncio  # type: ignore
async def test_query_with_value_projection(creds: str, kind: str,
                                           project: str) -> None:
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)
        # setup test data
        await ds.insert(Key(project, [PathElement(kind)]), {'value': 30}, s)
        projection = [Projection.from_repr({'property': {'name': 'value'}})]

        query = Query(kind=kind, limit=1,
                      projection=projection)
        result = await ds.runQuery(query, session=s)
        assert result.entity_result_type.value == 'PROJECTION'
        # clean up test data
        await ds.delete(result.entity_results[0].entity.key, s)

@pytest.mark.asyncio  # type: ignore
async def test_query_with_distinct_on(creds: str, kind: str,
                                      project: str) -> None:
    keys1 = [Key(project, [PathElement(kind)]) for i in range(3)]
    keys2 = [Key(project, [PathElement(kind)]) for i in range(3)]
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        # setup test data
        allocatedKeys1 = await ds.allocateIds(keys1, session=s)
        allocatedKeys2 = await ds.allocateIds(keys2, session=s)
        for key1 in allocatedKeys1:
            await ds.insert(key1, {'dist_value': 11}, s)
        for key2 in allocatedKeys2:
            await ds.insert(key2, {'dist_value': 22}, s)
        query = Query(kind=kind, limit=10, distinct_on=['dist_value'])
        result = await ds.runQuery(query, session=s)
        assert len(result.entity_results) == 2
        # clean up test data
        for key1 in allocatedKeys1:
            await ds.delete(key1, s)
        for key2 in allocatedKeys2:
            await ds.delete(key2, s)


@pytest.mark.asyncio  # type: ignore
@pytest.mark.xfail(strict=False)  # type: ignore
async def test_query(creds: str, kind: str, project: str) -> None:
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        property_filter = PropertyFilter(
            prop='value', operator=PropertyFilterOperator.EQUAL,
            value=Value(42))
        query = Query(kind=kind, query_filter=Filter(property_filter))

        before = await ds.runQuery(query, session=s)
        num_results = len(before.entity_results)

        transaction = await ds.beginTransaction(session=s)
        mutations = [
            ds.make_mutation(Operation.INSERT,
                             Key(project, [PathElement(kind)]),
                             properties={'value': 42}),
            ds.make_mutation(Operation.INSERT,
                             Key(project, [PathElement(kind)]),
                             properties={'value': 42}),
        ]
        await ds.commit(mutations, transaction=transaction, session=s)

        after = await ds.runQuery(query, session=s)
        assert len(after.entity_results) == num_results + 2


@pytest.mark.asyncio  # type: ignore
@pytest.mark.xfail(strict=False)  # type: ignore
async def test_gql_query(creds: str, kind: str, project: str) -> None:
    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        query = GQLQuery(f'SELECT * FROM {kind} WHERE value = @value',
                         named_bindings={'value': 42})

        before = await ds.runQuery(query, session=s)
        num_results = len(before.entity_results)

        transaction = await ds.beginTransaction(session=s)
        mutations = [
            ds.make_mutation(Operation.INSERT,
                             Key(project, [PathElement(kind)]),
                             properties={'value': 42}),
            ds.make_mutation(Operation.INSERT,
                             Key(project, [PathElement(kind)]),
                             properties={'value': 42}),
            ds.make_mutation(Operation.INSERT,
                             Key(project, [PathElement(kind)]),
                             properties={'value': 42}),
        ]
        await ds.commit(mutations, transaction=transaction, session=s)

        after = await ds.runQuery(query, session=s)
        assert len(after.entity_results) == num_results + 3


@pytest.mark.skip
@pytest.mark.asyncio  # type: ignore
async def test_datastore_export(creds: str, project: str,
                                export_bucket_name: str):
    kind = 'PublicTestDatastoreExportModel'

    rand_uuid = str(uuid.uuid4())

    async with aiohttp.ClientSession(conn_timeout=10, read_timeout=10) as s:
        ds = Datastore(project=project, service_file=creds, session=s)

        await ds.insert(Key(project, [PathElement(kind)]),
                        properties={'rand_str': rand_uuid})

        operation = await ds.export(export_bucket_name, kinds=[kind])

        count = 0
        while (count < 10 and operation and
               operation.metadata['common']['state'] == 'PROCESSING'):
            await asyncio.sleep(10)
            operation = await ds.get_datastore_operation(operation.name)
            count += 1

        assert operation.metadata['common']['state'] == 'SUCCESSFUL'

        prefix_len = len(f'gs://{export_bucket_name}/')
        export_path = operation.metadata['outputUrlPrefix'][prefix_len:]

        storage = Storage(service_file=creds, session=s)
        files = await storage.list_objects(export_bucket_name,
                                           params={'prefix': export_path})
        for file in files['items']:
            await storage.delete(export_bucket_name, file['name'])
