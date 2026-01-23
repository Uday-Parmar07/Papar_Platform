from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    FloatProperty,
    BooleanProperty,
    RelationshipTo,
    RelationshipFrom,
    UniqueIdProperty,
)

class Subject(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(unique_index=True, required=True)
    has_topic = RelationshipTo('Topic', 'HAS_TOPIC')


class Topic(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(unique_index=True, required=True)
    belongs_to = RelationshipFrom('Subject', 'HAS_TOPIC')
    has_subtopic = RelationshipTo('SubTopic', 'HAS_SUBTOPIC')

class SubTopic(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(unique_index=True, required=True)
    belongs_to = RelationshipFrom('Topic', 'HAS_SUBTOPIC')
    has_concept = RelationshipTo('Concept', 'HAS_CONCEPT')

class Concept(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(unique_index=True, required=True)
    frequency = IntegerProperty(default=0)
    weight = FloatProperty(default=1.0)

    belongs_to = RelationshipFrom('SubTopic', 'HAS_CONCEPT')
    prerequisite_of = RelationshipTo('Concept', 'PREREQUISITE_OF')
    appears_in = RelationshipFrom('Question', 'APPEARS_IN')

class Question(StructuredNode):
    uid = UniqueIdProperty()
    text = StringProperty(required=True)
    year = IntegerProperty(required=True)
    marks = IntegerProperty(required=True)
    difficulty = StringProperty(
        choices={
            "easy": "easy",
            "medium": "medium",
            "hard": "hard",
        },
        required=True,
    )
    is_pyq = BooleanProperty(default=True)
    tests_concept = RelationshipTo('Concept', 'APPEARS_IN')

class Exam(StructuredNode):
    uid = UniqueIdProperty()
    name = StringProperty(required=True)  # e.g., GATE EE
    year = IntegerProperty(required=True)

    has_question = RelationshipTo("Question", "HAS_QUESTION")


class DifficultyProfile(StructuredNode):
    uid = UniqueIdProperty()
    level = StringProperty(
        choices={"Easy": "Easy", "Medium": "Medium", "Hard": "Hard"},
        unique_index=True
    )


class MarksProfile(StructuredNode):
    uid = UniqueIdProperty()
    marks = IntegerProperty(unique_index=True)