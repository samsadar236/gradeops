class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)
    # ADD THIS LINE:
    session_id = Column(String, nullable=False, default="public", index=True) 
    
    title = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rubrics = relationship("Rubric", back_populates="exam", cascade="all, delete-orphan")
    papers = relationship("Paper", back_populates="exam", cascade="all, delete-orphan")