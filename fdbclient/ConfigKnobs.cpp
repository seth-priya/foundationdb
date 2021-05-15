/*
 * ConfigKnobs.cpp
 *
 * This source file is part of the FoundationDB open source project
 *
 * Copyright 2013-2018 Apple Inc. and the FoundationDB project authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "fdbclient/ConfigKnobs.h"
#include "fdbclient/Tuple.h"
#include "flow/UnitTest.h"

ConfigKey ConfigKeyRef::decodeKey(KeyRef const& key) {
	auto tuple = Tuple::unpack(key);
	ASSERT(tuple.size() == 2); // TODO: Fail gracefully
	if (tuple.getType(0) == Tuple::NULL_TYPE) {
		return ConfigKeyRef({}, tuple.getString(1));
	} else {
		return ConfigKeyRef(tuple.getString(0), tuple.getString(1));
	}
}

TEST_CASE("/fdbclient/ConfigDB/ConfigKey/EncodeDecode") {
	Tuple tuple;
	tuple << "class-A"_sr
	      << "test_long"_sr;
	auto packed = tuple.pack();
	auto unpacked = ConfigKeyRef::decodeKey(packed);
	ASSERT(unpacked.configClass.get() == "class-A"_sr);
	ASSERT(unpacked.knobName == "test_long"_sr);
	return Void();
}
